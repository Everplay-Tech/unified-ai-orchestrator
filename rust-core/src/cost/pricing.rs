use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelPricing {
    pub input_price_per_1m: f64,
    pub output_price_per_1m: f64,
}

#[derive(Debug, Clone)]
pub struct PricingTable {
    prices: HashMap<String, ModelPricing>,
}

impl PricingTable {
    pub fn new() -> Self {
        let mut prices = HashMap::new();
        
        // Claude pricing (as of 2024)
        prices.insert(
            "claude-3-5-sonnet-20241022".to_string(),
            ModelPricing {
                input_price_per_1m: 3.0,
                output_price_per_1m: 15.0,
            },
        );
        prices.insert(
            "claude-3-opus-20240229".to_string(),
            ModelPricing {
                input_price_per_1m: 15.0,
                output_price_per_1m: 75.0,
            },
        );
        prices.insert(
            "claude-3-sonnet-20240229".to_string(),
            ModelPricing {
                input_price_per_1m: 3.0,
                output_price_per_1m: 15.0,
            },
        );
        prices.insert(
            "claude-3-haiku-20240307".to_string(),
            ModelPricing {
                input_price_per_1m: 0.25,
                output_price_per_1m: 1.25,
            },
        );
        
        // GPT pricing
        prices.insert(
            "gpt-4".to_string(),
            ModelPricing {
                input_price_per_1m: 30.0,
                output_price_per_1m: 60.0,
            },
        );
        prices.insert(
            "gpt-4-turbo".to_string(),
            ModelPricing {
                input_price_per_1m: 10.0,
                output_price_per_1m: 30.0,
            },
        );
        prices.insert(
            "gpt-3.5-turbo".to_string(),
            ModelPricing {
                input_price_per_1m: 0.5,
                output_price_per_1m: 1.5,
            },
        );
        
        // Perplexity pricing
        prices.insert(
            "llama-3.1-sonar-large-128k-online".to_string(),
            ModelPricing {
                input_price_per_1m: 0.2,
                output_price_per_1m: 0.2,
            },
        );
        
        // Gemini pricing
        prices.insert(
            "gemini-pro".to_string(),
            ModelPricing {
                input_price_per_1m: 0.5,
                output_price_per_1m: 1.5,
            },
        );
        
        Self { prices }
    }
    
    pub fn get_pricing(&self, tool: &str, model: &str) -> Option<&ModelPricing> {
        // Try tool-model combination first
        let key = format!("{}-{}", tool, model);
        if let Some(pricing) = self.prices.get(&key) {
            return Some(pricing);
        }
        
        // Try just model
        self.prices.get(model)
    }
    
    pub fn calculate_cost(
        &self,
        tool: &str,
        model: &str,
        input_tokens: u32,
        output_tokens: u32,
    ) -> f64 {
        if let Some(pricing) = self.get_pricing(tool, model) {
            let input_cost = (input_tokens as f64 / 1_000_000.0) * pricing.input_price_per_1m;
            let output_cost = (output_tokens as f64 / 1_000_000.0) * pricing.output_price_per_1m;
            input_cost + output_cost
        } else {
            0.0
        }
    }
}

impl Default for PricingTable {
    fn default() -> Self {
        Self::new()
    }
}
