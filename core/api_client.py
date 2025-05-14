import requests
import json
import logging

logger = logging.getLogger(__name__)

class SocialMediaAPI:
    def __init__(self, api_key):
        self.api_url = "https://therealowlet.com/api/v2"
        self.api_key = api_key
        
    def _make_request(self, data):
        try:
            logger.info(f"Making API request: {data}")
            response = requests.post(
                self.api_url,
                data=data,
                headers={'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.01; Windows NT 5.0)'}
            )
            response_data = response.json()
            logger.info(f"API response: {response_data}")
            return response_data
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return {"error": str(e)}
    
    def get_services(self):
        """Get all available services from the API provider"""
        return self._make_request({
            'key': self.api_key,
            'action': 'services'
        })
        
    def create_order(self, service_id, link, quantity, **kwargs):
        """Create a new order with the API provider"""
        data = {
            'key': self.api_key,
            'action': 'add',
            'service': service_id,
            'link': link,
            'quantity': quantity
        }
        data.update(kwargs)
        return self._make_request(data)
    
    def get_order_status(self, order_id):
        """Check the status of an existing order"""
        return self._make_request({
            'key': self.api_key,
            'action': 'status',
            'order': order_id
        })
    
    def get_multiple_order_status(self, order_ids):
        """Check the status of multiple orders at once"""
        return self._make_request({
            'key': self.api_key,
            'action': 'status',
            'orders': ','.join(str(order_id) for order_id in order_ids)
        })
    
    def get_balance(self):
        """Check the current balance with the API provider"""
        return self._make_request({
            'key': self.api_key,
            'action': 'balance'
        })