/// File system watcher for incremental indexing

use notify::{Watcher, RecursiveMode, Event, EventKind};
use std::path::PathBuf;
use std::sync::mpsc;
use std::time::Duration;
use crate::indexer::codebase::CodebaseIndexer;

pub struct FileWatcher {
    watcher: notify::RecommendedWatcher,
    receiver: mpsc::Receiver<Result<Event, notify::Error>>,
    indexer: CodebaseIndexer,
    debounce_duration: Duration,
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
        })
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
            // Check for events with timeout
            match self.receiver.try_recv() {
                Ok(Ok(event)) => {
                    pending_events.push(event);
                    last_event_time = std::time::Instant::now();
                }
                Ok(Err(e)) => {
                    eprintln!("Watcher error: {}", e);
                }
                Err(mpsc::TryRecvError::Empty) => {
                    // If we have pending events and enough time has passed, process them
                    if !pending_events.is_empty() 
                        && last_event_time.elapsed() >= self.debounce_duration 
                    {
                        self.process_pending_events(&mut pending_events).await?;
                    }
                    
                    // Small sleep to avoid busy waiting
                    tokio::time::sleep(Duration::from_millis(100)).await;
                }
                Err(mpsc::TryRecvError::Disconnected) => {
                    return Err("Watcher channel disconnected".to_string());
                }
            }
        }
    }
    
    async fn process_pending_events(&mut self, events: &mut Vec<Event>) -> Result<(), String> {
        // Group events by path to avoid duplicate processing
        let mut paths_to_update = std::collections::HashSet::new();
        
        for event in events.drain(..) {
            match event.kind {
                EventKind::Create(_) | EventKind::Modify(_) => {
                    for path in event.paths {
                        if path.is_file() {
                            paths_to_update.insert(path);
                        }
                    }
                }
                EventKind::Remove(_) => {
                    for path in event.paths {
                        if path.is_file() {
                            // Remove from index
                            self.indexer.remove_file(&path).await?;
                        }
                    }
                }
                _ => {}
            }
        }
        
        // Update indexed files
        for path in paths_to_update {
            if let Err(e) = self.indexer.update_file(&path).await {
                eprintln!("Failed to index {}: {}", path.display(), e);
            }
        }
        
        Ok(())
    }
}
