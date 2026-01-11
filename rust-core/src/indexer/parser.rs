/// AST parsing using tree-sitter

use tree_sitter::{Language, Parser, Tree};
use std::collections::HashMap;
use std::path::Path;

// Import tree-sitter language grammars
use tree_sitter_python;
use tree_sitter_rust;
use tree_sitter_javascript;
use tree_sitter_typescript;

#[derive(Debug, Clone)]
pub struct CodeBlock {
    pub block_type: String, // function, class, method, etc.
    pub name: Option<String>,
    pub content: String,
    pub start_line: usize,
    pub end_line: usize,
    pub language: String,
    pub docstring: Option<String>, // Docstring or leading comments
    pub decorators: Vec<String>, // Python decorators or Rust attributes
}

pub struct ASTParser {
    parsers: HashMap<String, Parser>,
}

impl ASTParser {
    pub fn new() -> Self {
        let mut parsers = HashMap::new();
        
        // Initialize parsers for supported languages with tree-sitter grammars
        unsafe {
            // Python
            let mut python_parser = Parser::new();
            if python_parser.set_language(tree_sitter_python()).is_ok() {
                parsers.insert("python".to_string(), python_parser);
            }
            
            // Rust
            let mut rust_parser = Parser::new();
            if rust_parser.set_language(tree_sitter_rust()).is_ok() {
                parsers.insert("rust".to_string(), rust_parser);
            }
            
            // JavaScript
            let mut js_parser = Parser::new();
            if js_parser.set_language(tree_sitter_javascript()).is_ok() {
                parsers.insert("javascript".to_string(), js_parser);
            }
            
            // TypeScript
            let mut ts_parser = Parser::new();
            if ts_parser.set_language(tree_sitter_typescript()).is_ok() {
                parsers.insert("typescript".to_string(), ts_parser);
            }
        }
        
        Self { parsers }
    }
    
    pub fn parse_file(&mut self, content: &str, language: &str) -> Result<Vec<CodeBlock>, String> {
        // Get or create parser for language
        let parser = self.parsers
            .entry(language.to_string())
            .or_insert_with(|| {
                // Try to initialize parser for this language
                let mut p = Parser::new();
                match language {
                    "python" => {
                        if p.set_language(tree_sitter_python::language()).is_ok() {
                            return p;
                        }
                    }
                    "rust" => {
                        if p.set_language(tree_sitter_rust::language()).is_ok() {
                            return p;
                        }
                    }
                    "javascript" => {
                        if p.set_language(tree_sitter_javascript::language()).is_ok() {
                            return p;
                        }
                    }
                    "typescript" => {
                        if p.set_language(tree_sitter_typescript::language()).is_ok() {
                            return p;
                        }
                    }
                    _ => {}
                }
                // Return uninitialized parser if language not supported
                p
            });
        
        // Check if parser has a language set
        if parser.language().is_none() {
            return Err(format!("Language '{}' not supported or grammar failed to load", language));
        }
        
        // Parse the content
        let tree = parser.parse(content, None)
            .ok_or_else(|| format!("Failed to parse {} code", language))?;
        
        // Extract code blocks
        self.extract_blocks(&tree, content, language)
    }
    
    fn extract_blocks(&self, tree: &Tree, content: &str, language: &str) -> Result<Vec<CodeBlock>, String> {
        let mut blocks = Vec::new();
        let root_node = tree.root_node();
        
        // Extract blocks based on language
        match language {
            "python" => self.extract_python_blocks(&root_node, content, &mut blocks),
            "rust" => self.extract_rust_blocks(&root_node, content, &mut blocks),
            "javascript" | "typescript" => self.extract_js_blocks(&root_node, content, &mut blocks),
            _ => {
                // Generic extraction: find function-like structures
                self.extract_generic_blocks(&root_node, content, &mut blocks, language);
            }
        }
        
        Ok(blocks)
    }
    
    fn extract_python_blocks(&self, node: &tree_sitter::Node, content: &str, blocks: &mut Vec<CodeBlock>) {
        // Extract functions and classes
        let mut cursor = node.walk();
        self.traverse_node(&mut cursor, content, blocks, "python");
    }
    
    fn extract_rust_blocks(&self, node: &tree_sitter::Node, content: &str, blocks: &mut Vec<CodeBlock>) {
        // Extract functions, structs, impls, etc.
        let mut cursor = node.walk();
        self.traverse_node(&mut cursor, content, blocks, "rust");
    }
    
    fn extract_js_blocks(&self, node: &tree_sitter::Node, content: &str, blocks: &mut Vec<CodeBlock>) {
        // Extract functions, classes, methods
        let mut cursor = node.walk();
        self.traverse_node(&mut cursor, content, blocks, "javascript");
    }
    
    fn extract_generic_blocks(&self, node: &tree_sitter::Node, content: &str, blocks: &mut Vec<CodeBlock>, language: &str) {
        let mut cursor = node.walk();
        self.traverse_node(&mut cursor, content, blocks, language);
    }
    
    fn traverse_node(
        &self,
        cursor: &mut tree_sitter::TreeCursor,
        content: &str,
        blocks: &mut Vec<CodeBlock>,
        language: &str,
    ) {
        let node = cursor.node();
        let node_type = node.kind();
        
        // Extract relevant node types (actual tree-sitter node types)
        let relevant_types = match language {
            "python" => vec!["function_definition", "class_definition", "decorated_definition", "async_function_definition"],
            "rust" => vec!["function_item", "struct_item", "impl_item", "trait_item", "enum_item", "mod_item"],
            "javascript" | "typescript" => vec!["function_declaration", "class_declaration", "method_definition", "arrow_function", "function", "async_function_declaration"],
            _ => vec!["function", "class", "method"],
        };
        
        if relevant_types.contains(&node_type) {
            let start_byte = node.start_byte();
            let end_byte = node.end_byte();
            let start_line = node.start_position().row;
            let end_line = node.end_position().row;
            
            let block_content = &content[start_byte..end_byte];
            
            // Try to extract name (with nested structure support)
            let name = self.extract_name(&node, content);
            
            // Extract docstring/comments
            let docstring = self.extract_docstring(&node, content, language);
            
            // Extract decorators/attributes
            let decorators = self.extract_decorators(&node, content, language);
            
            let block = CodeBlock {
                block_type: node_type.to_string(),
                name,
                content: block_content.to_string(),
                start_line,
                end_line,
                language: language.to_string(),
                docstring,
                decorators,
            };
            
            // Validate block before adding
            if self.validate_block(&block) {
                blocks.push(block);
            }
        }
        
        // Traverse children
        if cursor.goto_first_child() {
            loop {
                self.traverse_node(cursor, content, blocks, language);
                if !cursor.goto_next_sibling() {
                    break;
                }
            }
            cursor.goto_parent();
        }
    }
    
    fn extract_name(&self, node: &tree_sitter::Node, content: &str) -> Option<String> {
        // Try to find name node - handle nested structures
        let mut cursor = node.walk();
        
        // For nested structures (e.g., Class.method), build full name
        let mut name_parts = Vec::new();
        
        // First, try to find direct identifier
        if cursor.goto_first_child() {
            loop {
                let child = cursor.node();
                let child_kind = child.kind();
                
                // Handle different identifier types
                if child_kind == "identifier" || child_kind == "type_identifier" {
                    let start = child.start_byte();
                    let end = child.end_byte();
                    name_parts.push(content[start..end].to_string());
                }
                // Handle nested structures (e.g., qualified_name in Python)
                else if child_kind == "attribute" || child_kind == "member_expression" {
                    // Extract nested name
                    if let Some(nested_name) = self.extract_nested_name(&child, content) {
                        name_parts.push(nested_name);
                    }
                }
                
                if !cursor.goto_next_sibling() {
                    break;
                }
            }
        }
        
        if !name_parts.is_empty() {
            Some(name_parts.join("."))
        } else {
            None
        }
    }
    
    fn extract_nested_name(&self, node: &tree_sitter::Node, content: &str) -> Option<String> {
        let mut parts = Vec::new();
        let mut cursor = node.walk();
        
        if cursor.goto_first_child() {
            loop {
                let child = cursor.node();
                if child.kind() == "identifier" || child.kind() == "type_identifier" {
                    let start = child.start_byte();
                    let end = child.end_byte();
                    parts.push(content[start..end].to_string());
                }
                if !cursor.goto_next_sibling() {
                    break;
                }
            }
        }
        
        if !parts.is_empty() {
            Some(parts.join("."))
        } else {
            None
        }
    }
    
    fn extract_docstring(&self, node: &tree_sitter::Node, content: &str, language: &str) -> Option<String> {
        // Find docstring or leading comments before the node
        let node_start = node.start_byte();
        
        // Look backwards for docstring/comment patterns
        match language {
            "python" => {
                // Python docstrings are usually the first statement in a block
                // Look for string literals at the start
                let mut cursor = node.walk();
                if cursor.goto_first_child() {
                    loop {
                        let child = cursor.node();
                        if child.kind() == "expression_statement" {
                            let mut expr_cursor = child.walk();
                            if expr_cursor.goto_first_child() {
                                let expr_child = expr_cursor.node();
                                if expr_child.kind() == "string" {
                                    let start = expr_child.start_byte();
                                    let end = expr_child.end_byte();
                                    let doc = &content[start..end];
                                    // Remove quotes
                                    let cleaned = doc.trim_matches(|c| c == '"' || c == '\'' || c == '`');
                                    if !cleaned.is_empty() {
                                        return Some(cleaned.to_string());
                                    }
                                }
                            }
                        }
                        if !cursor.goto_next_sibling() {
                            break;
                        }
                    }
                }
            }
            "rust" => {
                // Rust doc comments are /// or //!
                // Look for doc comments before the node
                let before_content = &content[..node_start.min(content.len())];
                let lines: Vec<&str> = before_content.lines().rev().take(10).collect();
                let mut doc_lines = Vec::new();
                
                for line in lines.iter().rev() {
                    let trimmed = line.trim();
                    if trimmed.starts_with("///") || trimmed.starts_with("//!") {
                        let doc_line = trimmed.trim_start_matches("///").trim_start_matches("//!").trim();
                        if !doc_line.is_empty() {
                            doc_lines.push(doc_line.to_string());
                        }
                    } else if trimmed.is_empty() || trimmed.starts_with("//") {
                        continue;
                    } else {
                        break;
                    }
                }
                
                if !doc_lines.is_empty() {
                    return Some(doc_lines.join("\n"));
                }
            }
            _ => {
                // Generic: look for block comments
                let before_content = &content[..node_start.min(content.len())];
                if let Some(last_comment) = before_content.rfind("/*") {
                    if let Some(comment_end) = before_content[last_comment..].find("*/") {
                        let comment = &before_content[last_comment + 2..last_comment + comment_end];
                        let cleaned = comment.trim();
                        if !cleaned.is_empty() {
                            return Some(cleaned.to_string());
                        }
                    }
                }
            }
        }
        
        None
    }
    
    fn extract_decorators(&self, node: &tree_sitter::Node, content: &str, language: &str) -> Vec<String> {
        let mut decorators = Vec::new();
        
        match language {
            "python" => {
                // Python decorators are before function/class definitions
                let mut cursor = node.walk();
                if cursor.goto_first_child() {
                    loop {
                        let child = cursor.node();
                        if child.kind() == "decorator" {
                            let start = child.start_byte();
                            let end = child.end_byte();
                            decorators.push(content[start..end].trim().to_string());
                        }
                        if !cursor.goto_next_sibling() {
                            break;
                        }
                    }
                }
            }
            "rust" => {
                // Rust attributes are #[...] or #![...]
                let mut cursor = node.walk();
                if cursor.goto_first_child() {
                    loop {
                        let child = cursor.node();
                        if child.kind() == "attribute_item" {
                            let start = child.start_byte();
                            let end = child.end_byte();
                            decorators.push(content[start..end].trim().to_string());
                        }
                        if !cursor.goto_next_sibling() {
                            break;
                        }
                    }
                }
            }
            _ => {}
        }
        
        decorators
    }
    
    fn validate_block(&self, block: &CodeBlock) -> bool {
        // Minimum size validation
        if block.content.len() < 10 {
            return false;
        }
        
        // Check for valid name if block type requires it
        match block.block_type.as_str() {
            "function_definition" | "function_item" | "function_declaration" => {
                // Functions should have names (except anonymous/lambda functions)
                if block.name.is_none() && !block.content.contains("lambda") && !block.content.contains("=>") {
                    // Might be anonymous, but check if it's actually a function
                    return block.content.contains("fn ") || block.content.contains("def ") || block.content.contains("function");
                }
            }
            "class_definition" | "class_declaration" => {
                // Classes should have names
                if block.name.is_none() {
                    return false;
                }
            }
            _ => {}
        }
        
        true
    }
    
    pub fn detect_language(file_path: &Path) -> Option<String> {
        let ext = file_path.extension()?.to_str()?;
        
        match ext {
            "py" => Some("python".to_string()),
            "rs" => Some("rust".to_string()),
            "js" => Some("javascript".to_string()),
            "ts" => Some("typescript".to_string()),
            "tsx" => Some("typescript".to_string()),
            "go" => Some("go".to_string()),
            "java" => Some("java".to_string()),
            "cpp" | "cc" | "cxx" => Some("cpp".to_string()),
            "c" => Some("c".to_string()),
            _ => None,
        }
    }
}

impl Default for ASTParser {
    fn default() -> Self {
        Self::new()
    }
}
