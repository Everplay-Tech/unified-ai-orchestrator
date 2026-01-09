/// Codebase indexer module

pub mod parser;
pub mod codebase;
pub mod semantic;
pub mod watcher;
pub mod search;
pub mod storage;

pub use codebase::CodebaseIndexer;
pub use parser::ASTParser;
pub use semantic::EmbeddingGenerator;
pub use watcher::FileWatcher;
pub use search::SemanticSearch;
