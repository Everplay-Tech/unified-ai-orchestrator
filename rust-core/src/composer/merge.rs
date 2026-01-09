use super::{ComposedResponse, ToolResponse};

pub fn merge_responses(responses: Vec<ToolResponse>) -> ComposedResponse {
    if responses.is_empty() {
        return ComposedResponse {
            content: String::new(),
            sources: Vec::new(),
            metadata: None,
        };
    }

    if responses.len() == 1 {
        let resp = &responses[0];
        return ComposedResponse {
            content: resp.content.clone(),
            sources: vec![resp.tool.clone()],
            metadata: resp.metadata.clone(),
        };
    }

    // Simple merge: combine all responses with source attribution
    let mut content_parts = Vec::new();
    let mut sources = Vec::new();

    for (idx, resp) in responses.iter().enumerate() {
        sources.push(resp.tool.clone());
        content_parts.push(format!(
            "--- Response from {} ---\n{}\n",
            resp.tool, resp.content
        ));
    }

    ComposedResponse {
        content: content_parts.join("\n"),
        sources,
        metadata: None,
    }
}
