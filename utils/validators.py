from utils.exceptions import ValidationError

class InputValidator:
    """Validator for input parameters."""
    
    def validate_data_request(self, args):
        coin_id = args.get('coin_id', 'bitcoin')
        days = args.get('days', '30')
        exchange = args.get('exchange')
        group = args.get('group')
        
        try:
            days = int(days)
            if not (1 <= days <= 365):
                raise ValueError
        except ValueError:
            raise ValidationError("Days must be an integer between 1 and 365")
        
        # Add more validation as needed
        return {
            'coin_id': coin_id,
            'days': days,
            'exchange': exchange,
            'group': group
        }
    
    def validate_integer_param(self, value, name, min_val, max_val):
        try:
            val = int(value)
            if not (min_val <= val <= max_val):
                raise ValueError
            return val
        except ValueError:
            raise ValidationError(f"{name} must be an integer between {min_val} and {max_val}")
