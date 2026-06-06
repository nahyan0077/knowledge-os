from knowledge_os.application.ports import PricingService


class ConfigPricingService(PricingService):
    def __init__(self, pricing_dict: dict[str, dict[str, float]]) -> None:
        self._pricing = pricing_dict

    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        model_lower = model.lower()
        matched_key = "default"
        for key in self._pricing:
            if key != "default" and key in model_lower:
                matched_key = key
                break

        rates = self._pricing[matched_key]
        input_rate = rates["input_rate_per_million"] / 1_000_000
        output_rate = rates["output_rate_per_million"] / 1_000_000

        return input_tokens * input_rate + output_tokens * output_rate
