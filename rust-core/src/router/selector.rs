use super::analyzer::TaskType;
use std::collections::HashMap;

pub fn select_tools(
    task_type: &TaskType,
    routing_rules: &HashMap<String, Vec<String>>,
    default_tool: &str,
) -> Vec<String> {
    let rule_key = match task_type {
        TaskType::CodeEditing => "code_editing",
        TaskType::Research => "research",
        TaskType::GeneralChat => "general_chat",
        TaskType::CodeGeneration => "code_editing", // Use code_editing rules
        TaskType::TerminalAutomation => "general_chat", // Fallback
        TaskType::Unknown => "general_chat",
    };

    routing_rules
        .get(rule_key)
        .cloned()
        .unwrap_or_else(|| vec![default_tool.to_string()])
}
