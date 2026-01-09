use super::pricing::PricingTable;

pub struct CostCalculator {
    pricing_table: PricingTable,
}

impl CostCalculator {
    pub fn new() -> Self {
        Self {
            pricing_table: PricingTable::new(),
        }
    }
    
    pub fn calculate(
        &self,
        tool: &str,
        model: &str,
        input_tokens: u32,
        output_tokens: u32,
    ) -> f64 {
        self.pricing_table.calculate_cost(tool, model, input_tokens, output_tokens)
    }
}

impl Default for CostCalculator {
    fn default() -> Self {
        Self::new()
    }
}
