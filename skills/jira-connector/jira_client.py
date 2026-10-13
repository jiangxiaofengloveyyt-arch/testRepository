#!/usr/bin/env python3
"""
JIRA Connector Client - Reusable Python client for JIRA Server.
Supports multiple authentication methods:
1. PAT Token (Recommended - simplest)
2. Username + Password
3. nginx Basic Auth + JIRA Session (legacy)
"""
import os
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import base64
import time
from typing import Dict, Any, Optional, List

# Load config from file
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
_config = {}
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        _config = json.load(f)


class JiraClient:
    """JIRA Server client with multiple authentication support."""
    
    def __init__(self):
        """Initialize from environment variables. Auto-detects auth method."""
        # Default credentials: config file > environment variables > hardcoded defaults
        self.base_url = os.environ.get('JIRA_BASE_URL', _config.get('base_url', 'http://bug.new-see.com:8088')).rstrip('/')
        self.ctx = ssl._create_unverified_context()
        
        # Auth credentials
        self.token = os.environ.get('JIRA_TOKEN', '')
        self.jira_user = os.environ.get('JIRA_USER', _config.get('jira_user', 'airobot'))
        self.jira_pass = os.environ.get('JIRA_PASS', _config.get('jira_pass', 'develop1111'))
        self.nginx_user = os.environ.get('JIRA_NGINX_USER', _config.get('nginx_user', 'newsee'))
        self.nginx_pass = os.environ.get('JIRA_NGINX_PASS', _config.get('nginx_pass', 'newsee'))
        
        # Determine auth method
        if not self.base_url:
            raise ValueError("JIRA_BASE_URL is required")
        
        if self.token:
            self.auth_method = 'token'
        elif self.jira_user and self.jira_pass and self.nginx_user and self.nginx_pass:
            self.auth_method = 'dual'
            self.session_id: Optional[str] = None
            self.auth_header = 'Basic ' + base64.b64encode(f"{self.nginx_user}:{self.nginx_pass}".encode()).decode()
        elif self.jira_user and self.jira_pass:
            self.auth_method = 'simple'
            self.session_id: Optional[str] = None
        else:
            raise ValueError(
                "Missing authentication credentials. Set one of:\n"
                "  - JIRA_BASE_URL + JIRA_TOKEN (Recommended)\n"
                "  - JIRA_BASE_URL + JIRA_USER + JIRA_PASS\n"
                "  - JIRA_BASE_URL + JIRA_USER + JIRA_PASS + JIRA_NGINX_USER + JIRA_NGINX_PASS"
            )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get auth headers based on auth method."""
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        
        if self.auth_method == 'token':
            headers['Authorization'] = f'Bearer {self.token}'
        elif self.auth_method == 'simple':
            if self.session_id:
                headers['Cookie'] = f'JSESSIONID={self.session_id}'
        elif self.auth_method == 'dual':
            headers['Authorization'] = self.auth_header
            if self.session_id:
                headers['Cookie'] = f'JSESSIONID={self.session_id}'
        
        return headers
    
    def login(self) -> str:
        """Login to JIRA and get session ID (for non-token auth)."""
        if self.auth_method == 'token':
            return ''  # No login needed for token auth
        
        data = json.dumps({'username': self.jira_user, 'password': self.jira_pass}).encode()
        headers = {'Content-Type': 'application/json'}
        
        if self.auth_method == 'dual':
            headers['Authorization'] = self.auth_header
        
        req = urllib.request.Request(
            f'{self.base_url}/rest/auth/1/session',
            data=data,
            headers=headers
        )
        
        try:
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=60)
            self.session_id = json.loads(resp.read())['session']['value']
            return self.session_id
        except urllib.error.HTTPError as e:
            raise ValueError(f"Login failed (HTTP {e.code}): {e.reason}")
    
    def api(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated API call."""
        if self.auth_method != 'token' and not self.session_id:
            self.login()
        
        url = f'{self.base_url}{endpoint}' if not endpoint.startswith('http') else endpoint
        headers = self._get_headers()
        
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)
        
        try:
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=60)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 401 and self.auth_method != 'token':
                # Session expired, retry once
                try:
                    self.login()
                    headers = self._get_headers()
                    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
                    resp = urllib.request.urlopen(req, context=self.ctx, timeout=60)
                    return json.loads(resp.read())
                except:
                    pass
            raise ValueError(f"API call failed (HTTP {e.code}): {e.reason}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection and return server info."""
        return self.api('/rest/api/2/serverInfo')
    
    def get_issue(self, key: str, expand: Optional[str] = None) -> Dict[str, Any]:
        """Get issue by key.
        
        Args:
            key: Issue key (e.g., 'ITOPS-123')
            expand: Optional expand parameter (e.g., 'changelog' to get attachment history)
        """
        endpoint = f'/rest/api/2/issue/{key}'
        if expand:
            endpoint += f'?expand={expand}'
        return self.api(endpoint)
    
    def get_issue_attachments(self, key: str) -> List[Dict[str, Any]]:
        """Get all attachments for an issue.
        
        Note: JIRA's attachment field is not always returned in the standard fields.
        This method uses the changelog to extract attachment information.
        
        Args:
            key: Issue key (e.g., 'ITOPS-123')
            
        Returns:
            List of attachment dicts with keys: id, filename, created, author, content_url
        """
        # Get issue with changelog
        data = self.get_issue(key, expand='changelog')
        
        attachments = []
        
        # Method 1: Try to get from standard attachment field
        fields = data.get('fields', {})
        if 'attachment' in fields:
            for att in fields.get('attachment', []):
                attachments.append({
                    'id': att.get('id'),
                    'filename': att.get('filename'),
                    'mimeType': att.get('mimeType'),
                    'size': att.get('size'),
                    'created': att.get('created'),
                    'author': att.get('author', {}).get('displayName'),
                    'content_url': att.get('content')
                })
        
        # Method 2: Extract from changelog (for cases where attachment field is not returned)
        if not attachments:
            changelog = data.get('changelog', {})
            histories = changelog.get('histories', [])
            
            for h in histories:
                items = h.get('items', [])
                for item in items:
                    if item.get('field') == 'Attachment' and item.get('to'):
                        att_id = item.get('to')
                        filename = item.get('toString')
                        
                        # Get attachment metadata
                        try:
                            att_data = self.get_attachment(att_id)
                            attachments.append({
                                'id': att_id,
                                'filename': filename,
                                'mimeType': att_data.get('mimeType'),
                                'size': att_data.get('size'),
                                'created': h.get('created'),
                                'author': h.get('author', {}).get('displayName'),
                                'content_url': att_data.get('content') or f"{self.base_url}/secure/attachment/{att_id}/{filename}"
                            })
                        except:
                            # If we can't get metadata, use basic info from changelog
                            attachments.append({
                                'id': att_id,
                                'filename': filename,
                                'created': h.get('created'),
                                'author': h.get('author', {}).get('displayName'),
                                'content_url': f"{self.base_url}/secure/attachment/{att_id}/{filename}"
                            })
        
        return attachments
    
    def get_attachment(self, attachment_id: str) -> Dict[str, Any]:
        """Get attachment metadata by ID.
        
        Args:
            attachment_id: Attachment ID
            
        Returns:
            Attachment metadata dict
        """
        return self.api(f'/rest/api/2/attachment/{attachment_id}')
    
    def search(self, jql: str, fields: Optional[List[str]] = None, 
               max_results: int = 50, start_at: int = 0) -> Dict[str, Any]:
        """Search issues with JQL."""
        params = {'jql': jql, 'maxResults': max_results, 'startAt': start_at}
        if fields:
            params['fields'] = ','.join(fields)
        query = urllib.parse.urlencode(params)
        return self.api(f'/rest/api/2/search?{query}')
    
    def search_all(self, jql: str, fields: Optional[List[str]] = None, 
                   delay: float = 0.5) -> List[Dict[str, Any]]:
        """Search all issues with pagination."""
        all_issues = []
        start = 0
        while True:
            data = self.search(jql, fields=fields, max_results=100, start_at=start)
            issues = data.get('issues', [])
            all_issues.extend(issues)
            total = data.get('total', 0)
            if start + len(issues) >= total:
                break
            start += 100
            time.sleep(delay)
        return all_issues
    
    def create_issue(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Create new issue."""
        return self.api('/rest/api/2/issue', method='POST', data={'fields': fields})
    
    def update_issue(self, key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Update issue fields. Returns None on success (HTTP 204)."""
        if self.auth_method != 'token' and not self.session_id:
            self.login()

        url = f'{self.base_url}/rest/api/2/issue/{key}'
        headers = self._get_headers()
        payload = json.dumps({'fields': fields}, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers=headers, method='PUT')

        try:
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=60)
            # PUT returns 204 No Content on success
            if resp.code == 204:
                return {'success': True}
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise ValueError(f"Update issue failed (HTTP {e.code}): {e.reason}")
    
    def get_project(self, key: str) -> Dict[str, Any]:
        """Get project info."""
        return self.api(f'/rest/api/2/project/{key}')
    
    def get_components(self, project_key: str) -> List[Dict[str, Any]]:
        """Get project components."""
        return self.api(f'/rest/api/2/project/{project_key}/components')
    
    def get_priorities(self) -> List[Dict[str, Any]]:
        """Get all priorities."""
        return self.api('/rest/api/2/priority')
    
    def get_statuses(self) -> List[Dict[str, Any]]:
        """Get all statuses."""
        return self.api('/rest/api/2/status')
    
    def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add comment to issue."""
        return self.api(f'/rest/api/2/issue/{issue_key}/comment', method='POST', data={'body': comment})
    
    def get_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get all comments for an issue."""
        result = self.api(f'/rest/api/2/issue/{issue_key}/comment')
        return result.get('comments', [])
    
    def get_user(self, username: str) -> Dict[str, Any]:
        """Get user info by username."""
        return self.api(f'/rest/api/2/user?username={urllib.parse.quote(username)}')
    
    def search_users(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search users by query."""
        return self.api(f'/rest/api/2/user/search?username={urllib.parse.quote(query)}&maxResults={max_results}')
    
    def get_worklog(self, issue_key: str) -> Dict[str, Any]:
        """Get worklog for an issue."""
        return self.api(f'/rest/api/2/issue/{issue_key}/worklog')

    def get_fields(self) -> List[Dict[str, Any]]:
        """Get all available fields in JIRA, including custom fields with their IDs."""
        return self.api('/rest/api/2/field')

    def search_fields_by_name(self, keyword: str) -> List[Dict[str, Any]]:
        """Search fields by name (Chinese or English). Returns matching field info including ID."""
        all_fields = self.get_fields()
        return [f for f in all_fields if keyword.lower() in f.get('name', '').lower() or keyword.lower() in f.get('id', '').lower()]

    def transition_issue(self, issue_key: str, transition_name_or_id: str, fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Transition issue to a new status by transition name or ID.
        
        Args:
            issue_key: The issue key (e.g., 'ITOPS-123')
            transition_name_or_id: Transition name (e.g., '开始进行') or ID (e.g., '11')
            fields: Optional fields to set during transition (required for some transitions)
                   Example: {'customfield_12400': {'id': '15261'}} for 评价 field
        
        Returns:
            Dict with success status and transition name
        
        Raises:
            ValueError: If transition not found or HTTP error occurs
        """
        # Get available transitions for the issue
        transitions_url = f'{self.base_url}/rest/api/2/issue/{issue_key}/transitions'
        headers = self._get_headers()
        req = urllib.request.Request(transitions_url, headers=headers, method='GET')

        try:
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=60)
            data = json.loads(resp.read())
            transitions = data.get('transitions', [])

            # Find matching transition
            target_transition = None
            for t in transitions:
                if str(t.get('id')) == str(transition_name_or_id) or t.get('name', '').strip() == transition_name_or_id.strip():
                    target_transition = t
                    break

            if not target_transition:
                available_names = [t.get('name') for t in transitions]
                raise ValueError(f"Transition '{transition_name_or_id}' not found. Available transitions: {available_names}")

            # Execute transition with optional fields
            transition_url = f'{self.base_url}/rest/api/2/issue/{issue_key}/transitions'
            payload_data = {'transition': {'id': target_transition['id']}}
            if fields:
                payload_data['fields'] = fields
            payload = json.dumps(payload_data, ensure_ascii=False).encode('utf-8')
            req = urllib.request.Request(transition_url, data=payload, headers=headers, method='POST')
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=60)

            if resp.code == 204:
                return {'success': True, 'transition': target_transition['name']}
            return json.loads(resp.read())

        except urllib.error.HTTPError as e:
            error_msg = f"Transition issue failed (HTTP {e.code}): {e.reason}"
            try:
                if e.fp:
                    error_body = json.loads(e.fp.read().decode('utf-8'))
                    if 'errors' in error_body:
                        errors = error_body['errors']
                        error_details = '; '.join([f"{k}: {v}" for k, v in errors.items()])
                        error_msg += f" - {error_details}"
            except:
                pass
            raise ValueError(error_msg)

    def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get all available transitions for an issue.
        
        Returns:
            List of transition dicts with 'id', 'name', and 'to' status info
        """
        transitions_url = f'{self.base_url}/rest/api/2/issue/{issue_key}/transitions'
        headers = self._get_headers()
        req = urllib.request.Request(transitions_url, headers=headers, method='GET')
        
        resp = urllib.request.urlopen(req, context=self.ctx, timeout=60)
        data = json.loads(resp.read())
        return data.get('transitions', [])


def get_client() -> JiraClient:
    """Get configured JIRA client."""
    return JiraClient()


if __name__ == '__main__':
    # Test connection
    client = get_client()
    print(f"Auth method: {client.auth_method}")
    print(f"Connecting to: {client.base_url}")
    
    try:
        server_info = client.test_connection()
        print(f"Connected! JIRA Version: {server_info.get('version')}")
        print(f"Server Title: {server_info.get('serverTitle')}")
        print(f"Server Time: {server_info.get('serverTime')}")
    except Exception as e:
        print(f"Connection failed: {e}")
