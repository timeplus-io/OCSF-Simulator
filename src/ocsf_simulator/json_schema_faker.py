import random
from datetime import datetime, timedelta
from faker import Faker
from typing import Any, Dict, List, Union, Optional
import uuid
import time
import sys

from .geonames import get_random_city

# Optional OCSF library integration
try:
    from ocsf.util import get_schema
    OCSF_LIB_AVAILABLE = True
except ImportError:
    OCSF_LIB_AVAILABLE = False
    print("Warning: ocsf-lib-py not found. Install with: pip install ocsf-lib", file=sys.stderr)
    print("Falling back to manual schema mode.", file=sys.stderr)

class JSONSchemaFaker:
    """
    Enhanced JSON Schema fake data generator with comprehensive OCSF support.
    Integrates with ocsf-lib-py for dynamic schema retrieval and validation.
    """
    
    def __init__(self, locale='en_US', ocsf_version: Optional[str] = None):
        self.fake = Faker(locale)
        self.fake.seed_instance(random.randint(1, 10000))
        
        # OCSF integration
        self.ocsf_schema: Optional[Any] = None  # Use Any since we don't know the exact type
        self.ocsf_version = ocsf_version or "1.1.0"
        
        # Setup comprehensive data generators FIRST
        self.setup_custom_providers()
        self.setup_ocsf_objects()
        self.setup_cybersecurity_data()
        
        # Initialize OCSF schema AFTER cyber_data is set up
        if OCSF_LIB_AVAILABLE:
            self._load_ocsf_schema()
    
    def _load_ocsf_schema(self):
        """Load OCSF schema using ocsf-lib-py"""
        try:
            print(f"Loading OCSF schema version {self.ocsf_version}...", file=sys.stderr)
            self.ocsf_schema = get_schema(self.ocsf_version)
            print(f"Successfully loaded OCSF schema {self.ocsf_version}", file=sys.stderr)
            
            # Extract real data from schema
            self._extract_schema_data()
            
        except Exception as e:
            print(f"Warning: Could not load OCSF schema {self.ocsf_version}: {e}", file=sys.stderr)
            print("Falling back to manual schema mode.", file=sys.stderr)
            self.ocsf_schema = None
    
    def _extract_schema_data(self):
        """Extract real categories, classes, and enums from OCSF schema"""
        if not self.ocsf_schema:
            return
        
        try:
            # Debug: print schema type and available attributes
            print(f"Schema type: {type(self.ocsf_schema)}", file=sys.stderr)
            print(f"Schema attributes: {dir(self.ocsf_schema)}", file=sys.stderr)
            
            # Try to extract categories (handle different possible attribute names)
            real_categories = {}
            categories_attr = None
            for attr_name in ['categories', 'category', 'cats']:
                if hasattr(self.ocsf_schema, attr_name):
                    categories_attr = getattr(self.ocsf_schema, attr_name)
                    break
            
            if categories_attr:
                if hasattr(categories_attr, 'values'):
                    # If it's a dict-like object with values()
                    for category in categories_attr.values():
                        if hasattr(category, 'uid') and hasattr(category, 'caption'):
                            real_categories[category.uid] = category.caption
                elif isinstance(categories_attr, dict):
                    # If it's a regular dict
                    for key, category in categories_attr.items():
                        if hasattr(category, 'uid') and hasattr(category, 'caption'):
                            real_categories[category.uid] = category.caption
                        elif isinstance(category, dict) and 'uid' in category and 'caption' in category:
                            real_categories[category['uid']] = category['caption']
            
            # Try to extract event classes
            real_classes = {}
            classes_attr = None
            for attr_name in ['classes', 'class', 'events', 'event_classes']:
                if hasattr(self.ocsf_schema, attr_name):
                    classes_attr = getattr(self.ocsf_schema, attr_name)
                    break
            
            if classes_attr:
                if hasattr(classes_attr, 'values'):
                    # If it's a dict-like object with values()
                    for event_class in classes_attr.values():
                        if hasattr(event_class, 'uid') and hasattr(event_class, 'caption'):
                            real_classes[event_class.uid] = event_class.caption
                elif isinstance(classes_attr, dict):
                    # If it's a regular dict
                    for key, event_class in classes_attr.items():
                        if hasattr(event_class, 'uid') and hasattr(event_class, 'caption'):
                            real_classes[event_class.uid] = event_class.caption
                        elif isinstance(event_class, dict) and 'uid' in event_class and 'caption' in event_class:
                            real_classes[event_class['uid']] = event_class['caption']
            
            # Try to extract profiles
            real_profiles = []
            profiles_attr = None
            for attr_name in ['profiles', 'profile']:
                if hasattr(self.ocsf_schema, attr_name):
                    profiles_attr = getattr(self.ocsf_schema, attr_name)
                    break
            
            if profiles_attr:
                if hasattr(profiles_attr, 'values'):
                    for profile in profiles_attr.values():
                        if hasattr(profile, 'caption'):
                            real_profiles.append(profile.caption.lower().replace(' ', '_'))
                elif isinstance(profiles_attr, dict):
                    for key, profile in profiles_attr.items():
                        if hasattr(profile, 'caption'):
                            real_profiles.append(profile.caption.lower().replace(' ', '_'))
                        elif isinstance(profile, dict) and 'caption' in profile:
                            real_profiles.append(profile['caption'].lower().replace(' ', '_'))
            
            # Update cyber_data with real OCSF data if we found any
            if real_categories:
                self.cyber_data['ocsf_categories'] = real_categories
                print(f"Extracted {len(real_categories)} categories", file=sys.stderr)
            
            if real_classes:
                self.cyber_data['ocsf_classes'] = real_classes
                print(f"Extracted {len(real_classes)} classes", file=sys.stderr)
                
            if real_profiles:
                self.cyber_data['ocsf_profiles'] = real_profiles
                print(f"Extracted {len(real_profiles)} profiles", file=sys.stderr)
            
            if not (real_categories or real_classes or real_profiles):
                print("Warning: Could not extract any data from OCSF schema. Using fallback data.", file=sys.stderr)
                
        except Exception as e:
            print(f"Warning: Could not extract data from OCSF schema: {e}", file=sys.stderr)
            print("Using fallback data.", file=sys.stderr)
    
    def get_ocsf_class_schema(self, class_uid: int) -> Optional[Dict[str, Any]]:
        """Get schema for a specific OCSF event class"""
        if not self.ocsf_schema:
            return None
            
        try:
            event_class = self.ocsf_schema.classes.get(class_uid)
            if not event_class:
                return None
                
            # Convert to dictionary format for our generator
            schema = {
                'attributes': []
            }
            
            # Add attributes from the event class
            for attr_name, attr_def in event_class.attributes.items():
                attr_schema = {
                    attr_name: {
                        'type': attr_def.type,
                        'description': attr_def.description,
                        'requirement': attr_def.requirement,
                        'is_array': attr_def.is_array
                    }
                }
                
                # Add enum values if present
                if hasattr(attr_def, 'enum') and attr_def.enum:
                    attr_schema[attr_name]['enum'] = attr_def.enum
                    
                schema['attributes'].append(attr_schema)
                
            return schema
            
        except Exception as e:
            print(f"Warning: Could not get schema for class {class_uid}: {e}", file=sys.stderr)
            return None
    
    def generate_ocsf_event(self, class_uid: int, profiles: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate a realistic OCSF event for a specific class UID
        
        Args:
            class_uid: OCSF event class UID (e.g., 3002 for Authentication)
            profiles: Optional list of OCSF profiles to apply
            
        Returns:
            Generated OCSF event
        """
        # Get schema for the class if available
        class_schema = self.get_ocsf_class_schema(class_uid)
        
        if class_schema:
            # Use real schema
            event = self.generate_from_schema(class_schema)
        else:
            # Fallback to manual generation
            event = self._generate_manual_ocsf_event(class_uid)
        
        # Ensure required OCSF fields are present
        event = self._ensure_ocsf_required_fields(event, class_uid, profiles)
        
        return event
    
    def _generate_manual_ocsf_event(self, class_uid: int) -> Dict[str, Any]:
        """Generate OCSF event manually when schema is not available"""
        category_uid = class_uid // 1000  # Extract category from class UID
        
        base_event = {
            'activity_id': random.randint(1, 10),
            'category_uid': category_uid,
            'class_uid': class_uid,
            'severity_id': random.randint(1, 4),
            'time': int(datetime.now().timestamp() * 1000),
            'metadata': self._generate_metadata_object()
        }
        
        # Add class-specific attributes based on class UID
        if class_uid == 3002:  # Authentication
            base_event.update(self._generate_authentication_specific())
        elif class_uid == 4001:  # Network Activity
            base_event.update(self._generate_network_activity_specific())
        elif class_uid == 1001:  # File System Activity
            base_event.update(self._generate_file_activity_specific())
        elif class_uid == 1007:  # Process Activity
            base_event.update(self._generate_process_activity_specific())
        elif class_uid == 2001:  # Security Finding
            base_event.update(self._generate_security_finding_specific())
        
        return base_event
    
    def _ensure_ocsf_required_fields(self, event: Dict[str, Any], class_uid: int, profiles: Optional[List[str]] = None) -> Dict[str, Any]:
        """Ensure all required OCSF fields are present and valid"""
        
        # Calculate type_uid if not present
        if 'type_uid' not in event and 'class_uid' in event and 'activity_id' in event:
            event['type_uid'] = event['class_uid'] * 100 + event['activity_id']
        
        # Add type_name based on class_uid and activity_id
        if 'type_name' not in event:
            class_name = self.cyber_data['ocsf_classes'].get(class_uid, 'Unknown Activity')
            activity_name = self._get_activity_name(event.get('activity_id', 1))
            event['type_name'] = f"{class_name}: {activity_name}"
        
        # Add category_name
        if 'category_name' not in event and 'category_uid' in event:
            event['category_name'] = self.cyber_data['ocsf_categories'].get(event['category_uid'], 'Unknown')
        
        # Add class_name
        if 'class_name' not in event:
            event['class_name'] = self.cyber_data['ocsf_classes'].get(class_uid, 'Unknown Activity')
        
        # Add activity_name
        if 'activity_name' not in event and 'activity_id' in event:
            event['activity_name'] = self._get_activity_name(event['activity_id'])
        
        # Add severity name
        if 'severity' not in event and 'severity_id' in event:
            severity_map = {0: 'Unknown', 1: 'Informational', 2: 'Low', 3: 'Medium', 4: 'High', 5: 'Critical', 6: 'Fatal'}
            event['severity'] = severity_map.get(event['severity_id'], 'Unknown')
        
        # Add status fields if missing
        if 'status_id' not in event:
            event['status_id'] = random.choice([1, 2])  # Success or Failure
        if 'status' not in event:
            status_map = {0: 'Unknown', 1: 'Success', 2: 'Failure', 99: 'Other'}
            event['status'] = status_map.get(event['status_id'], 'Unknown')
        
        # Apply profiles
        if profiles and 'metadata' in event:
            if 'profiles' not in event['metadata']:
                event['metadata']['profiles'] = profiles
        
        # Add observables for key fields
        if 'observables' not in event:
            event['observables'] = self._generate_observables_for_event(event)
        
        return event
    
    def _get_activity_name(self, activity_id: int) -> str:
        """Get activity name for activity ID"""
        activity_names = {
            1: 'Open', 2: 'Close', 3: 'Reset', 4: 'Fail', 5: 'Refuse', 6: 'Traffic', 7: 'Listen',
            10: 'Create', 11: 'Read', 12: 'Update', 13: 'Delete', 14: 'Mount', 15: 'Unmount',
            20: 'Launch', 21: 'Terminate', 22: 'Inject', 23: 'Hook', 24: 'Set User ID',
            30: 'Logon', 31: 'Logoff', 32: 'Authentication Ticket', 33: 'Service Ticket'
        }
        return activity_names.get(activity_id, 'Other')
    
    def _generate_authentication_specific(self) -> Dict[str, Any]:
        """Generate Authentication event specific fields"""
        return {
            'user': self._generate_user_object(),
            'device': self._generate_device_object(),
            'src_endpoint': self._generate_network_endpoint_object(),
            'dst_endpoint': self._generate_network_endpoint_object(),
            'session': {
                'uid': str(uuid.uuid4()),
                'created_time': int(datetime.now().timestamp() * 1000),
                'is_remote': random.choice([True, False])
            },
            'logon_type': random.choice(self.cyber_data['logon_types']),
            'logon_type_id': random.randint(1, 10),
            'auth_protocol': random.choice(self.cyber_data['auth_protocols']),
            'auth_protocol_id': random.randint(1, 10),
            'is_cleartext': random.choice([True, False]),
            'is_mfa': random.choice([True, False])
        }
    
    def _generate_network_activity_specific(self) -> Dict[str, Any]:
        """Generate Network Activity event specific fields"""
        return {
            'src_endpoint': self._generate_network_endpoint_object(),
            'dst_endpoint': self._generate_network_endpoint_object(),
            'connection_info': self._generate_connection_info_object(),
            'traffic': self._generate_traffic_object(),
            'tls': self._generate_tls_object() if random.random() > 0.6 else None,
            'proxy_endpoint': self._generate_network_endpoint_object() if random.random() > 0.8 else None
        }
    
    def _generate_file_activity_specific(self) -> Dict[str, Any]:
        """Generate File System Activity event specific fields"""
        return {
            'file': self._generate_file_object(),
            'device': self._generate_device_object(),
            'actor': {
                'process': self._generate_process_object(),
                'user': self._generate_user_object()
            }
        }
    
    def _generate_process_activity_specific(self) -> Dict[str, Any]:
        """Generate Process Activity event specific fields"""
        return {
            'process': self._generate_process_object(),
            'actor': {
                'process': self._generate_process_object(),
                'user': self._generate_user_object()
            },
            'device': self._generate_device_object()
        }
    
    def _generate_security_finding_specific(self) -> Dict[str, Any]:
        """Generate Security Finding event specific fields"""
        return {
            'finding_info': {
                'title': self.fake.sentence(nb_words=6),
                'desc': self.fake.text(max_nb_chars=200),
                'uid': str(uuid.uuid4()),
                'created_time': int(datetime.now().timestamp() * 1000),
                'modified_time': int(datetime.now().timestamp() * 1000),
                'product_uid': str(uuid.uuid4()),
                'types': [random.choice(['TPM Violation', 'Malware', 'Configuration', 'Vulnerability'])]
            },
            'resources': [
                {
                    'name': self.fake.file_name(),
                    'type': 'File',
                    'uid': str(uuid.uuid4())
                }
            ],
            'malware': [self._generate_malware_object()] if random.random() > 0.7 else [],
            'vulnerabilities': [self._generate_vulnerability_object()] if random.random() > 0.8 else []
        }
    
    def _generate_observables_for_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate observables based on event content"""
        observables = []
        
        # Extract IPs
        for field in ['src_endpoint', 'dst_endpoint']:
            if field in event and isinstance(event[field], dict) and 'ip' in event[field]:
                observables.append({
                    'name': f"{field}.ip",
                    'type': 'IP Address',
                    'value': event[field]['ip']
                })
        
        # Extract file hashes
        if 'file' in event and isinstance(event['file'], dict) and 'hashes' in event['file']:
            for hash_obj in event['file']['hashes']:
                observables.append({
                    'name': 'file.hash',
                    'type': 'Hash',
                    'value': hash_obj['value']
                })
        
        # Extract user info
        if 'user' in event and isinstance(event['user'], dict):
            if 'name' in event['user']:
                observables.append({
                    'name': 'user.name',
                    'type': 'User Name',
                    'value': event['user']['name']
                })
            if 'email_addr' in event['user']:
                observables.append({
                    'name': 'user.email_addr',
                    'type': 'Email',
                    'value': event['user']['email_addr']
                })
        
        return observables[:5]  # Limit to 5 observables
    
    def setup_custom_providers(self):
        """Setup custom data generators for specific field types"""
        self.custom_generators = {
            # OCSF Scalar Data Types
            'string_t': lambda: self.fake.word(),
            'integer_t': lambda: random.randint(1, 1000),
            'long_t': lambda: random.randint(100000, 999999999),
            'float_t': lambda: round(random.uniform(0.1, 1000.0), 3),
            'boolean_t': lambda: random.choice([True, False]),
            'timestamp_t': lambda: int(datetime.now().timestamp() * 1000),  # Unix timestamp in milliseconds
            'datetime_t': lambda: self.fake.date_time_between(start_date='-1d', end_date='now').strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'json_t': lambda: self._generate_json_object(),
            'bytestring_t': lambda: self.fake.binary(length=32).hex(),
            
            # Network related
            'ip_t': lambda: self.fake.ipv4(),
            'ipv4': lambda: self.fake.ipv4(),
            'ipv6': lambda: self.fake.ipv6(),
            'ip': lambda: self.fake.ipv4(),
            'port': lambda: random.randint(1, 65535),
            'mac_t': lambda: self.fake.mac_address(),
            'mac': lambda: self.fake.mac_address(),
            'hostname': lambda: self.fake.domain_name(),
            'url_t': lambda: self.fake.url(),
            'url': lambda: self.fake.url(),
            'domain': lambda: self.fake.domain_name(),
            'subnet': lambda: f"{self.fake.ipv4()}/{random.randint(16, 30)}",
            
            # Security/Hash related
            'hash_t': lambda: self.fake.sha256(),
            'hash': lambda: self.fake.sha256(),
            'md5': lambda: self.fake.md5(),
            'sha1': lambda: self.fake.sha1(),
            'sha256': lambda: self.fake.sha256(),
            'uuid_t': lambda: str(uuid.uuid4()),
            'uuid': lambda: str(uuid.uuid4()),
            'fingerprint': lambda: self.fake.sha256()[:32],
            
            # File/process related
            'filename': lambda: self.fake.file_name(),
            'filepath': lambda: self.fake.file_path(),
            'file_path': lambda: self.fake.file_path(),
            'process_name': lambda: random.choice(['chrome.exe', 'firefox.exe', 'notepad.exe', 'cmd.exe', 'powershell.exe', 'svchost.exe', 'explorer.exe']),
            'app_name': lambda: random.choice(['chrome.exe', 'firefox.exe', 'outlook.exe', 'teams.exe', 'slack.exe', 'zoom.exe']),
            'command_line': lambda: self._generate_command_line(),
            'mime_type': lambda: random.choice(['application/json', 'text/html', 'image/png', 'application/pdf', 'text/plain']),
            
            # User/identity related
            'username': lambda: self.fake.user_name(),
            'user_name': lambda: self.fake.user_name(),
            'email_t': lambda: self.fake.email(),
            'email': lambda: self.fake.email(),
            'user_id': lambda: str(random.randint(1000, 9999)),
            'uid': lambda: str(random.randint(1000, 9999)),
            'sid': lambda: f"S-1-5-{random.randint(21, 32)}-{random.randint(1000000000, 9999999999)}-{random.randint(1000000000, 9999999999)}-{random.randint(1000000000, 9999999999)}-{random.randint(1000, 9999)}",
            
            # Protocol/network specific
            'protocol': lambda: random.choice(['TCP', 'UDP', 'ICMP', 'HTTP', 'HTTPS', 'FTP', 'SSH', 'DNS', 'DHCP']),
            'protocol_name': lambda: random.choice(['TCP', 'UDP', 'ICMP', 'HTTP', 'HTTPS', 'FTP', 'SSH']),
            'cipher': lambda: random.choice(['AES-256-GCM', 'TLS_AES_256_GCM_SHA384', 'ECDHE-RSA-AES256-GCM-SHA384', 'TLS_AES_128_GCM_SHA256']),
            'tls_version': lambda: random.choice(['1.2', '1.3']),
            
            # Threat intelligence
            'ioc': lambda: random.choice([self.fake.ipv4(), self.fake.domain_name(), self.fake.sha256()]),
            'cve': lambda: f"CVE-{random.randint(2015, 2025)}-{random.randint(1000, 99999)}",
            'severity': lambda: random.choice(['Low', 'Medium', 'High', 'Critical', 'Informational']),
            'disposition': lambda: random.choice(['Allowed', 'Blocked', 'Quarantined', 'Deleted', 'Restored']),
            
            # Timestamps and time-related
            'timestamp': lambda: int(datetime.now().timestamp() * 1000),
            'iso_timestamp': lambda: self.fake.date_time_between(start_date='-1d', end_date='now').isoformat() + 'Z',
            'epoch': lambda: int(time.time()),
            'duration': lambda: random.randint(100, 10000),  # milliseconds
            
            # Cloud/infrastructure
            'region': lambda: random.choice(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']),
            'availability_zone': lambda: random.choice(['us-east-1a', 'us-east-1b', 'us-west-2a', 'eu-west-1c']),
            'instance_id': lambda: f"i-{self.fake.lexify('??????????', letters='0123456789abcdef')}",
            'account_id': lambda: str(random.randint(100000000000, 999999999999)),
            
            # OCSF specific IDs and classifications based on official schema
            'activity_id': lambda: random.randint(1, 99),
            'category_uid': lambda: random.choice([1, 2, 3, 4, 5, 6]),  # Official OCSF categories
            'class_uid': lambda: random.choice([1001, 1002, 1003, 1004, 1005, 2001, 3001, 3002, 4001, 4002, 5001, 6001]),  # Real OCSF class UIDs
            'type_uid': lambda: self._generate_type_uid(),
            'severity_id': lambda: random.randint(0, 6),  # 0=Unknown, 1=Info, 2=Low, 3=Med, 4=High, 5=Critical, 6=Fatal
            'status_id': lambda: random.choice([0, 1, 2, 99]),  # Unknown, Success, Failure, Other
            'confidence': lambda: random.randint(1, 100),
            'risk_score': lambda: random.randint(1, 100),
            
            # Enhanced OCSF specific attributes based on dictionary.json
            'event_code': lambda: self.fake.lexify('???-####'),
            'cpid': lambda: str(uuid.uuid4()),  # Common Process Identifier
            'exit_code': lambda: random.choice([0, 1, -1, 126, 127]),
            'log_level': lambda: random.choice(['DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL']),
            'pattern_match': lambda: self.fake.sentence(nb_words=4),
            'raw_data': lambda: self.fake.text(max_nb_chars=200),
        }
    
    def setup_ocsf_objects(self):
        """Setup generators for common OCSF objects"""
        self.ocsf_objects = {
            'device': self._generate_device_object,
            'user': self._generate_user_object,
            'process': self._generate_process_object,
            'file': self._generate_file_object,
            'network_endpoint': self._generate_network_endpoint_object,
            'src_endpoint': self._generate_network_endpoint_object,
            'dst_endpoint': self._generate_network_endpoint_object,
            'proxy_endpoint': self._generate_network_endpoint_object,
            'network_traffic': self._generate_traffic_object,
            'traffic': self._generate_traffic_object,
            'network_connection_info': self._generate_connection_info_object,
            'connection_info': self._generate_connection_info_object,
            'tls': self._generate_tls_object,
            'certificate': self._generate_certificate_object,
            'metadata': self._generate_metadata_object,
            'observable': self._generate_observable_object,
            'enrichment': self._generate_enrichment_object,
            'malware': self._generate_malware_object,
            'vulnerability': self._generate_vulnerability_object,
            'actor': self._generate_actor_object,
            'attack': self._generate_attack_object,
            'api': self._generate_api_object,
            'database': self._generate_database_object,
            'organization': self._generate_organization_object,
            'cloud': self._generate_cloud_object,
            'container': self._generate_container_object,
        }
    
    def setup_cybersecurity_data(self):
        """Setup cybersecurity-specific data lists based on OCSF examples and standards"""
        self.cyber_data = {
            'attack_techniques': ['T1566', 'T1059', 'T1055', 'T1003', 'T1082', 'T1083', 'T1012', 'T1005', 'T1105', 'T1543'],
            'malware_families': ['Emotet', 'TrickBot', 'Ryuk', 'Cobalt Strike', 'Mimikatz', 'PowerShell Empire', 'Metasploit', 'Covenant'],
            'threat_actors': ['APT1', 'APT28', 'APT29', 'Lazarus Group', 'FIN7', 'Carbanak', 'Wizard Spider', 'Sandworm'],
            'log_levels': ['DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL', 'TRACE'],
            'event_outcomes': ['Success', 'Failure', 'Unknown', 'Other'],
            'directions': ['Inbound', 'Outbound', 'Lateral', 'Unknown'],
            'protocols': ['TCP', 'UDP', 'ICMP', 'HTTP', 'HTTPS', 'SSH', 'FTP', 'DNS', 'DHCP', 'SMTP', 'TLS', 'QUIC'],
            'os_types': ['Windows', 'Linux', 'macOS', 'iOS', 'Android', 'Unix', 'AIX', 'Solaris'],
            'browser_types': ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera', 'Internet Explorer'],
            
            # Based on OCSF official categories and classes
            'ocsf_categories': {
                1: 'System Activity',
                2: 'Findings', 
                3: 'Identity & Access Management',
                4: 'Network Activity',
                5: 'Discovery',
                6: 'Application Activity'
            },
            
            'ocsf_classes': {
                1001: 'File System Activity',
                1002: 'Kernel Extension Activity', 
                1003: 'Kernel Activity',
                1004: 'Memory Activity',
                1005: 'Module Activity',
                1006: 'Scheduled Job Activity',
                1007: 'Process Activity',
                2001: 'Security Finding',
                3001: 'Account Change',
                3002: 'Authentication',
                3003: 'Authorize Session',
                3004: 'Entity Management',
                3005: 'User Access Management',
                4001: 'Network Activity',
                4002: 'HTTP Activity',
                4003: 'DNS Activity',
                4004: 'DHCP Activity',
                4005: 'RDP Activity',
                4006: 'SMB Activity',
                4007: 'SSH Activity',
                4008: 'FTP Activity',
                4009: 'Email Activity',
                4010: 'Network File Activity',
                4011: 'Email File Activity',
                4012: 'Email URL Activity',
                5001: 'Device Inventory Info',
                5002: 'Device Config State',
                5003: 'User Inventory Info',
                6001: 'Web Resources Activity',
                6002: 'Application Lifecycle',
                6003: 'API Activity',
                6004: 'Web Resource Access Activity'
            },
            
            # Enhanced based on OCSF examples
            'disposition_values': ['Allowed', 'Blocked', 'Quarantined', 'Isolated', 'Deleted', 'Restored', 'Exonerated', 'Corrected', 'Partially Corrected', 'Uncorrected'],
            'logon_types': ['Interactive', 'Network', 'Batch', 'Service', 'Unlock', 'Network Cleartext', 'New Credentials', 'Remote Interactive', 'Cached Interactive'],
            'auth_protocols': ['NTLM', 'Kerberos', 'RADIUS', 'LDAP', 'OpenID', 'SAML', 'OAuth 2.0', 'Basic', 'Digest'],
            'cloud_providers': ['AWS', 'Microsoft Azure', 'Google Cloud Platform', 'Oracle Cloud', 'IBM Cloud', 'Alibaba Cloud'],
            'device_types': ['Computer', 'Mobile', 'Tablet', 'Server', 'IoT', 'Network', 'Virtual Machine', 'Container'],
            'file_types': ['Regular File', 'Directory', 'Symbolic Link', 'Block Device', 'Character Device', 'FIFO', 'Socket'],
            'process_integrities': ['Unknown', 'Untrusted', 'Low', 'Medium', 'High', 'System', 'Protected'],
        }
    
    def generate_from_schema(self, schema: Dict[str, Any], count: int = 1) -> Union[Dict, List[Dict]]:
        """
        Generate fake data based on JSON schema
        
        Args:
            schema: JSON schema dictionary
            count: Number of records to generate
            
        Returns:
            Generated fake data (single dict if count=1, list if count>1)
        """
        if count == 1:
            return self._generate_object(schema)
        else:
            return [self._generate_object(schema) for _ in range(count)]
    
    def _generate_object(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a single object based on schema"""
        result = {}
        
        # Handle OCSF-style schema with attributes array
        if 'attributes' in schema:
            return self._generate_from_ocsf_schema(schema)
        
        # Handle standard JSON schema
        if 'properties' in schema:
            for prop_name, prop_schema in schema['properties'].items():
                # Check if property is required
                required = schema.get('required', [])
                if prop_name in required or random.random() > 0.3:  # 70% chance for optional fields
                    result[prop_name] = self._generate_value(prop_name, prop_schema)
        
        return result
    
    def _generate_from_ocsf_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data from OCSF-style schema with attributes array"""
        result = {}
        
        for attr in schema.get('attributes', []):
            attr_name = list(attr.keys())[0]
            attr_config = attr[attr_name]
            
            # Check requirement level
            requirement = attr_config.get('requirement', 'optional')
            
            # Generate required fields, and some optional fields
            should_generate = (
                requirement == 'required' or 
                (requirement == 'recommended' and random.random() > 0.2) or
                (requirement == 'optional' and random.random() > 0.6)
            )
            
            if should_generate:
                result[attr_name] = self._generate_value_from_ocsf_attr(attr_name, attr_config)
        
        return result
    
    def _generate_value_from_ocsf_attr(self, attr_name: str, attr_config: Dict[str, Any]) -> Any:
        """Generate value for OCSF attribute"""
        attr_type = attr_config.get('type')
        is_array = attr_config.get('is_array', False)
        enum_values = attr_config.get('enum', {})
        object_type = attr_config.get('object_type')
        
        # Handle enums
        if enum_values:
            value = self._generate_enum_value(enum_values)
        # Handle object types
        elif object_type and object_type in self.ocsf_objects:
            value = self.ocsf_objects[object_type]()
        else:
            value = self._generate_by_type_and_name(attr_name, attr_type)
        
        # Handle arrays
        if is_array:
            array_size = random.randint(1, 3)
            return [value for _ in range(array_size)]
        
        return value
    
    def _generate_enum_value(self, enum_dict: Dict[str, Any]) -> Any:
        """Generate value from enum dictionary"""
        enum_keys = list(enum_dict.keys())
        # Filter out non-numeric keys for ID fields
        numeric_keys = [k for k in enum_keys if k.isdigit()]
        if numeric_keys:
            return int(random.choice(numeric_keys))
        return random.choice(enum_keys)
    
    def _generate_value(self, field_name: str, schema: Dict[str, Any]) -> Any:
        """Generate value based on field name and schema"""
        field_type = schema.get('type', 'string')
        
        # Handle arrays
        if field_type == 'array':
            items_schema = schema.get('items', {'type': 'string'})
            array_size = random.randint(1, 3)
            return [self._generate_value(f"{field_name}_item", items_schema) for _ in range(array_size)]
        
        # Handle objects
        if field_type == 'object':
            if 'properties' in schema:
                return self._generate_object(schema)
            else:
                return self._generate_generic_object(field_name)
        
        # Handle enums
        if 'enum' in schema:
            return random.choice(schema['enum'])
        
        return self._generate_by_type_and_name(field_name, field_type)
    
    def _generate_by_type_and_name(self, field_name: str, field_type: str) -> Any:
        """Generate value based on field name and type"""
        field_name_lower = field_name.lower()
        
        # Check custom generators first (exact matches)
        if field_type in self.custom_generators:
            return self.custom_generators[field_type]()
        
        # Check field name patterns
        for pattern, generator in self.custom_generators.items():
            if pattern in field_name_lower:
                return generator()
        
        # OCSF object type handling
        if field_type in self.ocsf_objects:
            return self.ocsf_objects[field_type]()
        
        # Type-based generation
        if field_type in ['integer_t', 'integer', 'int']:
            return self._generate_integer(field_name_lower)
        elif field_type in ['long_t', 'long']:
            return self._generate_long(field_name_lower)
        elif field_type in ['string_t', 'string', 'str']:
            return self._generate_string(field_name_lower)
        elif field_type in ['timestamp_t', 'timestamp']:
            return int(datetime.now().timestamp() * 1000)
        elif field_type in ['datetime_t', 'datetime']:
            return self.fake.date_time_between(start_date='-1d', end_date='now').strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        elif field_type in ['boolean_t', 'boolean', 'bool']:
            return random.choice([True, False])
        elif field_type in ['float_t', 'float', 'number']:
            return round(random.uniform(0, 1000), 2)
        elif field_type in ['json_t', 'json']:
            return self._generate_json_object()
        elif field_type in ['object_t', 'object']:
            return self._generate_generic_object(field_name)
        else:
            return self._generate_string(field_name_lower)
    
    def _generate_integer(self, field_name: str) -> int:
        """Generate integer based on field name context"""
        if any(x in field_name for x in ['id', 'uid']):
            return random.randint(1, 99999)
        elif 'port' in field_name:
            return random.randint(1, 65535)
        elif 'count' in field_name:
            return random.randint(1, 100)
        elif 'size' in field_name or 'bytes' in field_name:
            return random.randint(100, 1000000)
        elif 'duration' in field_name:
            return random.randint(100, 10000)  # milliseconds
        elif 'offset' in field_name:
            return random.randint(-720, 720)  # timezone offset
        elif 'score' in field_name:
            return random.randint(1, 100)
        elif 'confidence' in field_name:
            return random.randint(1, 100)
        else:
            return random.randint(1, 1000)
    
    def _generate_long(self, field_name: str) -> int:
        """Generate long integer based on field name context"""
        if 'timestamp' in field_name:
            return int(datetime.now().timestamp() * 1000)
        elif 'bytes' in field_name or 'size' in field_name:
            return random.randint(1000, 10000000)
        else:
            return random.randint(100000, 999999999)
    
    def _generate_string(self, field_name: str) -> str:
        """Generate string based on field name context"""
        if 'name' in field_name:
            if 'host' in field_name or 'computer' in field_name:
                return self.fake.domain_name()
            elif 'user' in field_name:
                return self.fake.user_name()
            elif 'file' in field_name:
                return self.fake.file_name()
            elif 'app' in field_name or 'application' in field_name:
                return random.choice(['Chrome', 'Firefox', 'Outlook', 'Teams', 'Slack'])
            else:
                return self.fake.word().title()
        elif 'description' in field_name or 'message' in field_name:
            return self.fake.sentence()
        elif 'version' in field_name:
            return f"{random.randint(1,9)}.{random.randint(0,9)}.{random.randint(0,9)}"
        elif 'code' in field_name:
            return self.fake.lexify('??###').upper()
        elif 'status' in field_name:
            return random.choice(['Success', 'Failure', 'Unknown', 'Other'])
        elif 'path' in field_name:
            return self.fake.file_path()
        elif 'command' in field_name:
            return self._generate_command_line()
        else:
            return self.fake.word()
    
    def _generate_json_object(self) -> Dict[str, Any]:
        """Generate a random JSON object"""
        obj = {}
        for _ in range(random.randint(2, 5)):
            key = self.fake.word()
            value_type = random.choice(['string', 'number', 'boolean', 'array'])
            if value_type == 'string':
                obj[key] = self.fake.word()
            elif value_type == 'number':
                obj[key] = random.randint(1, 100)
            elif value_type == 'boolean':
                obj[key] = random.choice([True, False])
            elif value_type == 'array':
                obj[key] = [self.fake.word() for _ in range(random.randint(1, 3))]
        return obj
    
    def _generate_command_line(self) -> str:
        """Generate a realistic command line"""
        commands = [
            'powershell.exe -ExecutionPolicy Bypass -Command',
            'cmd.exe /c',
            'wmic.exe process list',
            'netstat.exe -an',
            'ipconfig.exe /all',
            'tasklist.exe /svc',
        ]
        return random.choice(commands)
    
    # OCSF Object Generators
    def _generate_device_object(self) -> Dict[str, Any]:
        location = get_random_city()
        
        """Generate OCSF Device object based on official schema"""
        return {
            'name': self.fake.hostname(),
            'type': random.choice(self.cyber_data['device_types']),
            'type_id': random.randint(1, 8),
            'os': {
                'name': random.choice(self.cyber_data['os_types']),
                'version': f"{random.randint(1,9)}.{random.randint(0,9)}.{random.randint(0,9)}",
                'build': str(random.randint(1000, 99999)),
                'type': random.choice(['Windows', 'Linux', 'macOS', 'iOS', 'Android']),
                'type_id': random.randint(100, 999),
                'country': self.fake.country_code(),
                'sp_name': f"Service Pack {random.randint(1, 5)}",
                'sp_ver': str(random.randint(1, 5))
            },
            'ip': self.fake.ipv4(),
            'mac': self.fake.mac_address(),
            'hostname': self.fake.hostname(),
            'domain': self.fake.domain_name(),
            'instance_uid': str(uuid.uuid4()),
            'interface_name': random.choice(['eth0', 'wlan0', 'lo', 'ens33']),
            'interface_uid': str(uuid.uuid4()),
            'region': random.choice(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']),
            'subnet_uid': f"{self.fake.ipv4()}/{random.randint(16, 30)}",
            'uid': str(uuid.uuid4()),
            'hypervisor': random.choice(['VMware', 'Hyper-V', 'KVM', 'Xen']) if random.random() > 0.7 else None,
            'imei': self.fake.numerify('##############') if random.random() > 0.8 else None,
            'is_managed': random.choice([True, False]),
            'is_personal': random.choice([True, False]),
            'is_trusted': random.choice([True, False]),
            'location': {
                'city': location['name'],
                'country': location['country'],
                'region': self.fake.state(),
                'coordinates': [
                    location['longitude'],
                    location['latitude']
                ]
            },
            'owner': self._generate_user_object(),
            'risk_level': random.choice(['Low', 'Medium', 'High', 'Critical']),
            'risk_level_id': random.randint(1, 4)
        }
    
    def _generate_user_object(self) -> Dict[str, Any]:
        """Generate OCSF User object"""
        return {
            'name': self.fake.user_name(),
            'email_addr': self.fake.email(),
            'uid': str(random.randint(1000, 9999)),
            'org': {
                'name': self.fake.company(),
                'uid': str(uuid.uuid4())
            },
            'type': random.choice(['User', 'Admin', 'System', 'Service']),
            'domain': self.fake.domain_name(),
            'groups': [self.fake.word() for _ in range(random.randint(1, 3))]
        }
    
    def _generate_process_object(self) -> Dict[str, Any]:
        """Generate OCSF Process object"""
        return {
            'name': random.choice(['chrome.exe', 'firefox.exe', 'notepad.exe', 'cmd.exe']),
            'pid': random.randint(1000, 9999),
            'file': self._generate_file_object(),
            'user': self._generate_user_object(),
            'cmd_line': self._generate_command_line(),
            'created_time': int(datetime.now().timestamp() * 1000),
            'parent_process': {
                'name': 'explorer.exe',
                'pid': random.randint(100, 999)
            }
        }
    
    def _generate_file_object(self) -> Dict[str, Any]:
        """Generate OCSF File object"""
        return {
            'name': self.fake.file_name(),
            'path': self.fake.file_path(),
            'size': random.randint(1024, 1048576),
            'type': random.choice(['Regular File', 'Directory', 'Symbolic Link']),
            'mime_type': random.choice(['application/json', 'text/html', 'image/png']),
            'hashes': [
                {
                    'algorithm': 'SHA-256',
                    'value': self.fake.sha256()
                },
                {
                    'algorithm': 'MD5',
                    'value': self.fake.md5()
                }
            ],
            'created_time': int(datetime.now().timestamp() * 1000),
            'modified_time': int(datetime.now().timestamp() * 1000)
        }
    
    def _generate_network_endpoint_object(self) -> Dict[str, Any]:
        """Generate OCSF Network Endpoint object"""
        location = get_random_city()
        
        return {
            'ip': self.fake.ipv4(),
            'port': random.randint(1, 65535),
            'hostname': self.fake.domain_name(),
            'mac': self.fake.mac_address(),
            'domain': self.fake.domain_name(),
            'subnet_uid': f"{self.fake.ipv4()}/{random.randint(16, 30)}",
            'location': {
                'city': location['name'],
                'country': location['country'],
                'region': self.fake.state(),
                'coordinates': [
                    location['longitude'],
                    location['latitude']
                ]
            }
        }
    
    def _generate_traffic_object(self) -> Dict[str, Any]:
        """Generate OCSF Network Traffic object"""
        bytes_total = random.randint(1000, 100000)
        packets_total = random.randint(10, 1000)
        return {
            'bytes': bytes_total,
            'packets': packets_total,
            'bytes_in': random.randint(100, bytes_total // 2),
            'bytes_out': bytes_total - random.randint(100, bytes_total // 2),
            'packets_in': random.randint(5, packets_total // 2),
            'packets_out': packets_total - random.randint(5, packets_total // 2)
        }
    
    def _generate_connection_info_object(self) -> Dict[str, Any]:
        """Generate OCSF Network Connection Info object"""
        return {
            'protocol_name': random.choice(self.cyber_data['protocols']),
            'protocol_num': random.choice([6, 17, 1]),  # TCP, UDP, ICMP
            'direction': random.choice(self.cyber_data['directions']),
            'direction_id': random.randint(1, 4),
            'boundary': random.choice(['Internal', 'External', 'Unknown']),
            'boundary_id': random.randint(1, 3)
        }
    
    def _generate_tls_object(self) -> Dict[str, Any]:
        """Generate OCSF TLS object"""
        return {
            'version': random.choice(['1.2', '1.3']),
            'cipher': random.choice([
                'TLS_AES_256_GCM_SHA384',
                'TLS_AES_128_GCM_SHA256',
                'ECDHE-RSA-AES256-GCM-SHA384'
            ]),
            'certificate': self._generate_certificate_object(),
            'ja3_hash': self.fake.md5(),
            'ja3s_hash': self.fake.md5()
        }
    
    def _generate_certificate_object(self) -> Dict[str, Any]:
        """Generate OCSF Certificate object"""
        return {
            'subject': f"CN={self.fake.domain_name()}",
            'issuer': f"CN={self.fake.company()} CA",
            'serial_number': self.fake.lexify('????????????????', letters='0123456789ABCDEF'),
            'fingerprints': [
                {
                    'algorithm': 'SHA-256',
                    'value': self.fake.sha256()
                }
            ],
            'created_time': int(datetime.now().timestamp() * 1000),
            'expiration_time': int((datetime.now() + timedelta(days=365)).timestamp() * 1000)
        }
    
    def _generate_type_uid(self) -> int:
        """Generate realistic OCSF type_uid (class_uid * 100 + activity_id)"""
        class_uid = random.choice(list(self.cyber_data['ocsf_classes'].keys()))
        activity_id = random.randint(1, 10)
        return class_uid * 100 + activity_id
    
    def _generate_metadata_object(self) -> Dict[str, Any]:
        """Generate OCSF Metadata object based on official schema"""
        return {
            'version': '1.1.0',  # Current OCSF version
            'product': {
                'name': random.choice(['Security Manager', 'Endpoint Protection', 'Network Monitor', 'Cloud Guardian']),
                'version': f"{random.randint(1,9)}.{random.randint(0,9)}.{random.randint(0,9)}",
                'vendor_name': self.fake.company(),
                'uid': str(uuid.uuid4()),
                'lang': 'en',
                'url_string': self.fake.url()
            },
            'profiles': random.choice([
                ['cloud'],
                ['host'], 
                ['security_control'],
                ['cloud', 'security_control'],
                ['host', 'security_control']
            ]),
            'event_code': self.fake.lexify('???-####'),
            'log_name': random.choice(['Security', 'System', 'Application', 'Network', 'Audit']),
            'log_provider': self.fake.company(),
            'logged_time': int(datetime.now().timestamp() * 1000),
            'original_time': self.fake.date_time_between(start_date='-1d', end_date='now').isoformat() + 'Z',
            'processed_time': int(datetime.now().timestamp() * 1000),
            'correlation_uid': str(uuid.uuid4()),
            'extension': {
                'name': 'Custom Extension',
                'uid': str(uuid.uuid4()),
                'version': '1.0.0'
            }
        }
    
    def _generate_observable_object(self) -> Dict[str, Any]:
        """Generate OCSF Observable object"""
        obs_types = ['IP Address', 'Domain Name', 'URL', 'Hash', 'Email', 'User Agent', 'File Name']
        obs_type = random.choice(obs_types)
        
        value_map = {
            'IP Address': self.fake.ipv4(),
            'Domain Name': self.fake.domain_name(),
            'URL': self.fake.url(),
            'Hash': self.fake.sha256(),
            'Email': self.fake.email(),
            'User Agent': self.fake.user_agent(),
            'File Name': self.fake.file_name()
        }
        
        return {
            'name': random.choice(['src_endpoint.ip', 'dst_endpoint.ip', 'file.hash', 'user.email']),
            'type': obs_type,
            'value': value_map[obs_type],
            'reputation': {
                'score': random.randint(1, 100),
                'provider': random.choice(['VirusTotal', 'ThreatIntel', 'Internal'])
            }
        }
    
    def _generate_enrichment_object(self) -> Dict[str, Any]:
        """Generate OCSF Enrichment object"""
        return {
            'name': random.choice(['geo_location', 'threat_intel', 'user_context']),
            'value': self.fake.ipv4(),
            'type': random.choice(['location', 'reputation', 'context']),
            'data': {
                'provider': self.fake.company(),
                'score': random.randint(1, 100),
                'categories': [self.fake.word() for _ in range(random.randint(1, 3))]
            }
        }
    
    def _generate_malware_object(self) -> Dict[str, Any]:
        """Generate OCSF Malware object"""
        return {
            'name': random.choice(self.cyber_data['malware_families']),
            'classification': random.choice(['Trojan', 'Ransomware', 'Adware', 'Spyware']),
            'cves': [f"CVE-{random.randint(2015, 2025)}-{random.randint(1000, 99999)}" for _ in range(random.randint(0, 3))],
            'path': self.fake.file_path(),
            'provider': self.fake.company(),
            'uid': str(uuid.uuid4())
        }
    
    def _generate_vulnerability_object(self) -> Dict[str, Any]:
        """Generate OCSF Vulnerability object"""
        return {
            'cve': {
                'uid': f"CVE-{random.randint(2015, 2025)}-{random.randint(1000, 99999)}",
                'created_time': int(datetime.now().timestamp() * 1000),
                'modified_time': int(datetime.now().timestamp() * 1000)
            },
            'severity': random.choice(['Low', 'Medium', 'High', 'Critical']),
            'cvss': round(random.uniform(0.0, 10.0), 1),
            'desc': self.fake.sentence(),
            'title': self.fake.sentence(nb_words=6)
        }
    
    def _generate_actor_object(self) -> Dict[str, Any]:
        """Generate OCSF Actor/Threat Actor object"""
        return {
            'name': random.choice(self.cyber_data['threat_actors']),
            'type': random.choice(['Nation State', 'Cybercriminal', 'Hacktivist', 'Insider']),
            'uid': str(uuid.uuid4()),
            'session': {
                'uid': str(uuid.uuid4()),
                'created_time': int(datetime.now().timestamp() * 1000)
            }
        }
    
    def _generate_attack_object(self) -> Dict[str, Any]:
        """Generate OCSF Attack object with MITRE ATT&CK info"""
        return {
            'technique': {
                'name': random.choice(['Spearphishing Attachment', 'PowerShell', 'Process Injection']),
                'uid': random.choice(self.cyber_data['attack_techniques'])
            },
            'tactic': {
                'name': random.choice(['Initial Access', 'Execution', 'Defense Evasion']),
                'uid': f"TA{random.randint(1000, 9999)}"
            },
            'sub_technique': {
                'name': self.fake.sentence(nb_words=4),
                'uid': f"{random.choice(self.cyber_data['attack_techniques'])}.{random.randint(1, 9):03d}"
            }
        }
    
    def _generate_api_object(self) -> Dict[str, Any]:
        """Generate OCSF API object"""
        return {
            'operation': random.choice(['GET', 'POST', 'PUT', 'DELETE']),
            'service': {
                'name': random.choice(['S3', 'EC2', 'Lambda', 'CloudWatch']),
                'uid': str(uuid.uuid4())
            },
            'request': {
                'uid': str(uuid.uuid4()),
                'flags': [self.fake.word() for _ in range(random.randint(0, 2))]
            },
            'response': {
                'code': random.choice([200, 201, 400, 401, 403, 404, 500]),
                'message': random.choice(['OK', 'Created', 'Bad Request', 'Unauthorized', 'Forbidden'])
            }
        }
    
    def _generate_database_object(self) -> Dict[str, Any]:
        """Generate OCSF Database object"""
        return {
            'name': f"{self.fake.word()}_db",
            'type': random.choice(['MySQL', 'PostgreSQL', 'MongoDB', 'Redis']),
            'instance': f"db-{self.fake.lexify('????????', letters='0123456789abcdef')}",
            'uid': str(uuid.uuid4()),
            'size': random.randint(1000000, 100000000),  # bytes
        }
    
    def _generate_organization_object(self) -> Dict[str, Any]:
        """Generate OCSF Organization object"""
        return {
            'name': self.fake.company(),
            'uid': str(uuid.uuid4()),
            'ou_name': f"{self.fake.word().title()} Department",
            'ou_uid': str(uuid.uuid4())
        }
    
    def _generate_cloud_object(self) -> Dict[str, Any]:
        """Generate OCSF Cloud object"""
        return {
            'provider': random.choice(['AWS', 'Azure', 'GCP', 'Oracle Cloud']),
            'account': {
                'uid': str(random.randint(100000000000, 999999999999)),
                'name': self.fake.company()
            },
            'region': random.choice(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']),
            'zone': random.choice(['us-east-1a', 'us-east-1b', 'us-west-2a']),
            'project_uid': str(uuid.uuid4())
        }
    
    def _generate_container_object(self) -> Dict[str, Any]:
        """Generate OCSF Container object"""
        return {
            'name': f"{self.fake.word()}-container",
            'uid': f"container-{self.fake.lexify('????????????', letters='0123456789abcdef')}",
            'image': {
                'name': f"{self.fake.word()}:{random.choice(['latest', 'v1.0', 'stable'])}",
                'uid': f"sha256:{self.fake.sha256()}"
            },
            'pod_uid': str(uuid.uuid4()),
            'orchestrator': random.choice(['Kubernetes', 'Docker Swarm', 'ECS'])
        }
    
    def _generate_generic_object(self, field_name: str) -> Dict[str, Any]:
        """Generate a generic object based on field name"""
        field_name_lower = field_name.lower()
        
        # Check if we have a specific OCSF object generator
        for obj_type, generator in self.ocsf_objects.items():
            if obj_type in field_name_lower:
                return generator()
        
        # Fallback patterns
        if 'endpoint' in field_name_lower:
            return self._generate_network_endpoint_object()
        elif 'metadata' in field_name_lower:
            return self._generate_metadata_object()
        elif 'traffic' in field_name_lower:
            return self._generate_traffic_object()
        elif 'connection' in field_name_lower:
            return self._generate_connection_info_object()
        elif 'user' in field_name_lower:
            return self._generate_user_object()
        elif 'device' in field_name_lower:
            return self._generate_device_object()
        elif 'file' in field_name_lower:
            return self._generate_file_object()
        elif 'process' in field_name_lower:
            return self._generate_process_object()
        elif 'tls' in field_name_lower or 'ssl' in field_name_lower:
            return self._generate_tls_object()
        elif 'certificate' in field_name_lower or 'cert' in field_name_lower:
            return self._generate_certificate_object()
        elif 'malware' in field_name_lower:
            return self._generate_malware_object()
        elif 'vulnerability' in field_name_lower or 'vuln' in field_name_lower:
            return self._generate_vulnerability_object()
        elif 'actor' in field_name_lower or 'threat' in field_name_lower:
            return self._generate_actor_object()
        elif 'attack' in field_name_lower:
            return self._generate_attack_object()
        elif 'api' in field_name_lower:
            return self._generate_api_object()
        elif 'database' in field_name_lower or 'db' in field_name_lower:
            return self._generate_database_object()
        elif 'cloud' in field_name_lower:
            return self._generate_cloud_object()
        elif 'container' in field_name_lower:
            return self._generate_container_object()
        else:
            # Generic object with 2-4 random fields
            obj = {}
            for _ in range(random.randint(2, 4)):
                key = self.fake.word()
                obj[key] = random.choice([
                    self.fake.word(),
                    random.randint(1, 100),
                    self.fake.boolean()
                ])
            return obj
