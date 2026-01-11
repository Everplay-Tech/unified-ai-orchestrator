/// File system watcher for incremental indexing

use notify::{Watcher, RecursiveMode, Event, EventKind};
use std::path::PathBuf;
use std::sync::{mpsc, Arc};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;
use crate::indexer::codebase::CodebaseIndexer;

pub struct FileWatcher {
    watcher: notify::RecommendedWatcher,
    receiver: mpsc::Receiver<Result<Event, notify::Error>>,
    indexer: CodebaseIndexer,
    debounce_duration: Duration,
    shutdown: Arc<AtomicBool>,
}

impl FileWatcher {
    pub fn new(indexer: CodebaseIndexer) -> Result<Self, notify::Error> {
        let (tx, rx) = mpsc::channel();
        
        let watcher = notify::recommended_watcher(move |res| {
            tx.send(res).unwrap();
        })?;
        
        Ok(Self {
            watcher,
            receiver: rx,
            indexer,
            debounce_duration: Duration::from_millis(500),
            shutdown: Arc::new(AtomicBool::new(false)),
        })
    }
    
    pub fn shutdown_signal(&self) -> Arc<AtomicBool> {
        self.shutdown.clone()
    }
    
    pub fn watch(&mut self, path: PathBuf) -> Result<(), notify::Error> {
        self.watcher.watch(&path, RecursiveMode::Recursive)?;
        Ok(())
    }
    
    pub async fn process_events(&mut self) -> Result<(), String> {
        // Collect events with debouncing
        let mut pending_events = Vec::new();
        let mut last_event_time = std::time::Instant::now();
        
        loop {
            // Check for shutdown signal (no lock needed for atomic read)
            if self.shutdown.load(Ordering::Relaxed) {
                return Ok(());
            }
            
            // Check for events with timeout (receiver doesn't need mutex)
            match self.receiver.try_recv() {
                Ok(Ok(event)) => {
                    pending_events.push(event);
                    last_event_time = std::time::Instant::now();
                }
                Ok(Err(e)) => {
                    eprintln!("Watcher error: {}", e);
                    // Continue processing despite errors
                }
                Err(mpsc::TryRecvError::Empty) => {
                    // If we have pending events and enough time has passed, process them
                    // Only hold the lock during actual processing
                    if !pending_events.is_empty() 
                        && last_event_time.elapsed() >= self.debounce_duration 
                    {
                        if let Err(e) = self.process_pending_events(&mut pending_events).await {
                            eprintln!("Error processing file events: {}", e);
                            // Continue watching despite processing errors
                        }
                    }
                    
                    // Small sleep to avoid busy waiting (lock is released here)
                    tokio::time::sleep(Duration::from_millis(100)).await;
                }
                Err(mpsc::TryRecvError::Disconnected) => {
                    return Err("Watcher channel disconnected".to_string());
                }
            }
        }
    }
    
    /// Stop watching (cleanup)
    pub fn stop(&mut self) -> Result<(), notify::Error> {
        // Signal shutdown
        self.shutdown.store(true, Ordering::Relaxed);
        // Watcher will be dropped, which stops watching
        Ok(())
    }
    
    async fn process_pending_events(&mut self, events: &mut Vec<Event>) -> Result<(), String> {
        // Group events by path to avoid duplicate processing
        let mut paths_to_update = std::collections::HashSet::new();
        let mut paths_to_remove = std::collections::HashSet::new();
        
        for event in events.drain(..) {
            match event.kind {
                EventKind::Create(_) | EventKind::Modify(_) => {
                    for path in event.paths {
                        if path.is_file() {
                            // Only index supported languages
                            if crate::indexer::parser::ASTParser::detect_language(&path).is_some() {
                                paths_to_update.insert(path);
                            }
                        } else if path.is_dir() {
                            // For directories, we might want to index new files
                            // But for now, we'll skip directory creation events
                        }
                    }
                }
                EventKind::Remove(_) => {
                    for path in event.paths {
                        if path.is_file() {
                            paths_to_remove.insert(path);
                        }
                    }
                }
                _ => {}
            }
        }
        
        // Remove files from index first
        for path in paths_to_remove {
            if let Err(e) = self.indexer.remove_file(&path).await {
                eprintln!("Failed to remove {} from index: {}", path.display(), e);
                // Continue processing other files
            }
        }
        
        // Update indexed files (incremental indexing)
        for path in paths_to_update {
            // Skip if file doesn't exist (might have been deleted)
            if !path.exists() {
                continue;
            }
            
            // Use incremental indexing to check if file needs updating
            match self.indexer.should_index_file(&path).await {
                Ok(true) => {
                    if let Err(e) = self.indexer.update_file(&path).await {
                        eprintln!("Failed to index {}: {}", path.display(), e);
                    }
                }
                Ok(false) => {
                    // File hasn't changed, skip
                }
                Err(e) => {
                    eprintln!("Error checking if {} should be indexed: {}", path.display(), e);
                }
            }
        }
        
        Ok(())
    }
}
