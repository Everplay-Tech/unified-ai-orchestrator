use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum TaskType {
    CodeEditing,
    Research,
    GeneralChat,
    CodeGeneration,
    TerminalAutomation,
    Unknown,
}

pub fn analyze_request(message: &str) -> TaskType {
    let lower = message.to_lowercase();
    
    // Simple keyword-based classification
    if contains_code_keywords(&lower) {
        TaskType::CodeEditing
    } else if contains_research_keywords(&lower) {
        TaskType::Research
    } else if contains_terminal_keywords(&lower) {
        TaskType::TerminalAutomation
    } else if contains_generation_keywords(&lower) {
        TaskType::CodeGeneration
    } else {
        TaskType::GeneralChat
    }
}

fn contains_code_keywords(text: &str) -> bool {
    let keywords = [
        "refactor", "edit", "fix", "bug", "function", "class", "import",
        "code", "file", "module", "package", "syntax", "error", "compile",
        "test", "debug", "implement", "rewrite", "optimize",
    ];
    keywords.iter().any(|kw| text.contains(kw))
}

fn contains_research_keywords(text: &str) -> bool {
    let keywords = [
        "research", "find", "search", "what is", "explain", "how does",
        "information", "article", "paper", "source", "citation", "reference",
        "learn about", "tell me about", "investigate",
    ];
    keywords.iter().any(|kw| text.contains(kw))
}

fn contains_terminal_keywords(text: &str) -> bool {
    let keywords = [
        "run", "execute", "command", "terminal", "shell", "script",
        "automate", "workflow", "cli", "bash", "zsh",
    ];
    keywords.iter().any(|kw| text.contains(kw))
}

fn contains_generation_keywords(text: &str) -> bool {
    let keywords = [
        "generate", "create", "write", "make", "build", "new",
        "scaffold", "boilerplate", "template",
    ];
    keywords.iter().any(|kw| text.contains(kw))
}
