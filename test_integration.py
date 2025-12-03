import unittest
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import main
import config
from unittest.mock import patch, Mock

class MockAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/login':
            # Redirect to intermediate page
            self.send_response(302)
            self.send_header('Location', f'http://localhost:{self.server.server_port}/intermediate')
            self.end_headers()
            
        elif parsed_path.path == '/intermediate':
            # Redirect to example.com with success params
            # Note: In the real world this goes to example.com, but for the test
            # we want to verify that get_request_token follows redirects and parses the URL.
            # However, the code specifically checks for "example.com" in the netloc.
            # So we need to redirect to something that the code will accept.
            # The code checks: if parsed_url.netloc.startswith("example.com"):
            
            # Since we can't easily mock example.com without modifying /etc/hosts or using a proxy,
            # we might need to modify the code to accept localhost for testing, OR
            # we can rely on the fact that requests.get will try to fetch example.com.
            # But we want to avoid external network calls.
            
            # Wait, the code does:
            # response = requests.get(redirect_url, allow_redirects=False)
            # if parsed_url.netloc.startswith("example.com"): ...
            
            # If we redirect to http://example.com/..., requests.get will try to connect to it.
            # If we want to avoid external calls, we should probably mock `requests.get` in the test
            # OR we can just let it try to connect to example.com (which might be flaky or slow).
            
            # A better approach for an integration test that doesn't rely on external sites
            # but still tests the logic is to mock `requests.get` to return a dummy response
            # when it hits example.com, OR to change the code to allow a test domain.
            
            # Given the constraints, I will try to use `unittest.mock` to patch `requests.get` 
            # ONLY for the final call to example.com, but let the initial calls go to our local server.
            # Actually, `get_request_token` calls `requests.get` in a loop.
            
            # Let's try to redirect to a URL that *looks* like example.com but is actually our local server?
            # No, that won't work because the code checks `netloc`.
            
            # Let's redirect to `http://example.com/...` and patch `requests.get` to handle it.
            
            target_url = "http://example.com/?action=login&type=login&status=success&request_token=TEST_TOKEN"
            self.send_response(302)
            self.send_header('Location', target_url)
            self.end_headers()
            
        else:
            self.send_response(404)
            self.end_headers()

class TestGetRequestTokenIntegration(unittest.TestCase):
    def setUp(self):
        self.target_url = config.TARGET_URL
        if not self.target_url:
            # Start a local HTTP server in a separate thread
            self.server = HTTPServer(('localhost', 0), MockAuthHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            self.base_url = f'http://localhost:{self.server.server_port}'

    def tearDown(self):
        if not self.target_url:
            self.server.shutdown()
            self.server.server_close()

    def test_get_request_token_flow(self):
        if self.target_url:
            # E2E test with real URL
            print(f"Running E2E test against {self.target_url}")
            token = main.get_request_token(self.target_url)
            self.assertIsNotNone(token)
            print(f"Successfully retrieved token: {token}")
            return

        # Mock test with local server
        # We need to patch requests.get to intercept the call to example.com
        # but allow calls to localhost.
        
        original_get = main.requests.get
        
        def side_effect(url, **kwargs):
            if "example.com" in url:
                # Return a dummy response for example.com
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.headers = {} # No more redirects
                return mock_resp
            else:
                return original_get(url, **kwargs)
        
        with patch('main.requests.get', side_effect=side_effect):
            token = main.get_request_token(f'{self.base_url}/login')
            self.assertEqual(token, 'TEST_TOKEN')

if __name__ == '__main__':
    unittest.main()
