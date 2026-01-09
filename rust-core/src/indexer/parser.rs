/// AST parsing using tree-sitter

use tree_sitter::{Language, Parser, Tree};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct CodeBlock {
    pub block_type: String, // function, class, method, etc.
    pub name: Option<String>,
    pub content: String,
    pub start_line: usize,
    pub end_line: usize,
    pub language: String,
}

pub struct ASTParser {
    parsers: HashMap<String, Parser>,
}

impl ASTParser {
    pub fn new() -> Self {
        let mut parsers = HashMap::new();
        
        // Initialize parsers for supported languages
        // Note: In a real implementation, you'd load tree-sitter language grammars
        // For now, we'll create a basic parser structure
        
        Self { parsers }
    }
    
    pub fn parse_file(&mut self, content: &str, language: &str) -> Result<Vec<CodeBlock>, String> {
        // Get or create parser for language
        let parser = self.parsers
            .entry(language.to_string())
            .or_insert_with(|| {
                let mut p = Parser::new();
                // Set language based on file type
                // p.set_language(language).unwrap();
                p
            });
        
        // Parse the content
        let tree = parser.parse(content, None)
            .ok_or_else(|| "Failed to parse".to_string())?;
        
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
        
        // Extract relevant node types
        let relevant_types = match language {
            "python" => vec!["function_definition", "class_definition"],
            "rust" => vec!["function_item", "struct_item", "impl_item"],
            "javascript" => vec!["function_declaration", "class_declaration", "method_definition"],
            _ => vec!["function", "class", "method"],
        };
        
        if relevant_types.contains(&node_type) {
            let start_byte = node.start_byte();
            let end_byte = node.end_byte();
            let start_line = node.start_position().row;
            let end_line = node.end_position().row;
            
            let block_content = &content[start_byte..end_byte];
            
            // Try to extract name
            let name = self.extract_name(&node, content);
            
            blocks.push(CodeBlock {
                block_type: node_type.to_string(),
                name,
                content: block_content.to_string(),
                start_line,
                end_line,
                language: language.to_string(),
            });
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
        // Try to find name node
        let mut cursor = node.walk();
        if cursor.goto_first_child() {
            loop {
                let child = cursor.node();
                if child.kind() == "identifier" || child.kind() == "type_identifier" {
                    let start = child.start_byte();
                    let end = child.end_byte();
                    return Some(content[start..end].to_string());
                }
                if !cursor.goto_next_sibling() {
                    break;
                }
            }
        }
        None
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
