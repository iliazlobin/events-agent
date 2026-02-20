#!/usr/bin/env python3
"""
Sync Apify crawler schedules from crawler_schedules.yaml to Apify platform

Features:
- Read schedule config with defaults
- Validate memory, timeout, and schedule settings
- Create/update Apify schedules via API
- List current schedule configurations
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
except ImportError:
    print("Error: pyyaml not installed. Run: pip install pyyaml")
    sys.exit(1)

# requests is only needed for sync commands
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class ApifyScheduleManager:
    def __init__(self, config_path: Path, api_token: Optional[str] = None):
        self.config_path = config_path
        self.api_token = api_token or os.getenv('APIFY_API_TOKEN')

        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN not set (env var or parameter)")

        self.api_base = "https://api.apify.com/v2"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load schedule configuration from YAML"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _get_schedule_config(self, crawler_name: str) -> Dict[str, Any]:
        """Get full schedule config for a crawler (defaults + overrides)"""
        defaults = self.config.get('defaults', {})
        schedule_config = self.config.get('schedules', {}).get(crawler_name, {})

        # Merge defaults with schedule-specific config
        config = defaults.copy()
        config.update(schedule_config)

        return config

    def _validate_schedule(self, crawler_name: str, config: Dict[str, Any]) -> bool:
        """Validate schedule configuration"""
        errors = []

        # Validate required fields
        if 'actor_id' not in config:
            errors.append("actor_id is required")

        if 'cron' not in config:
            errors.append("cron expression is required")

        # Validate memory
        memory = config.get('memory_mbytes', 0)
        if memory <= 0:
            errors.append(f"memory_mbytes must be > 0, got {memory}")

        # Validate timeout
        timeout = config.get('timeout_secs', 0)
        if timeout <= 0:
            errors.append(f"timeout_secs must be > 0, got {timeout}")

        # Validate timezone
        if 'timezone' not in config:
            errors.append("timezone is required")

        if errors:
            print(f"❌ Validation errors for {crawler_name}:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

    def _build_schedule_payload(self, crawler_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build Apify schedule API payload"""
        return {
            "name": f"{crawler_name} - Daily Crawl",
            "isEnabled": config.get('enabled', True),
            "isExclusive": False,
            "cronExpression": config['cron'],
            "timezone": config['timezone'],
            "actorId": config['actor_id'],
            "input": config.get('input', {}),
            "options": {
                "build": config.get('build', 'latest'),
                "memoryMbytes": config['memory_mbytes'],
                "timeoutSecs": config['timeout_secs'],
            },
            "title": f"Events Crawler - {crawler_name.title()}",
            "description": f"Scheduled crawl for {crawler_name} events"
        }

    def _api_request(self, method: str, endpoint: str, data: Optional[Dict] = None):
        """Make authenticated API request to Apify"""
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library required for sync operations. Install: pip install requests")

        url = f"{self.api_base}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return response

    def list_schedules(self):
        """List all configured schedules from YAML"""
        print("\n=== Apify Crawler Schedules ===\n")

        schedules = self.config.get('schedules', {})

        for name in schedules.keys():
            config = self._get_schedule_config(name)

            print(f"📅 {name}")
            print(f"   Actor: {config.get('actor_id', 'N/A')}")
            print(f"   Cron: {config.get('cron', 'N/A')}")
            print(f"   Timezone: {config.get('timezone', 'N/A')}")
            print(f"   Memory: {config.get('memory_mbytes', 'N/A')} MB")
            print(f"   Timeout: {config.get('timeout_secs', 'N/A')}s")
            print(f"   Enabled: {config.get('enabled', False)}")

            # Show input preview
            input_data = config.get('input', {})
            if input_data:
                print(f"   Input: {json.dumps(input_data, indent=10)[:100]}...")

            print()

    def show_schedule(self, crawler_name: str):
        """Show detailed schedule configuration"""
        if crawler_name not in self.config.get('schedules', {}):
            print(f"❌ Schedule '{crawler_name}' not found")
            return

        config = self._get_schedule_config(crawler_name)

        print(f"\n=== {crawler_name} Schedule Configuration ===\n")
        print(yaml.dump(config, default_flow_style=False, sort_keys=False))

        # Validate
        if self._validate_schedule(crawler_name, config):
            print("✅ Schedule configuration is valid")

        # Show API payload
        print("\n=== Apify API Payload ===\n")
        payload = self._build_schedule_payload(crawler_name, config)
        print(json.dumps(payload, indent=2))

    def sync_schedule(self, crawler_name: str, dry_run: bool = False):
        """Sync a single schedule to Apify platform"""
        if crawler_name not in self.config.get('schedules', {}):
            print(f"❌ Schedule '{crawler_name}' not found")
            return False

        config = self._get_schedule_config(crawler_name)

        # Validate
        if not self._validate_schedule(crawler_name, config):
            return False

        # Build payload
        payload = self._build_schedule_payload(crawler_name, config)

        if dry_run:
            print(f"\n🔍 DRY RUN: Would create/update schedule for {crawler_name}")
            print(json.dumps(payload, indent=2))
            return True

        try:
            # Check if schedule exists
            # Note: We'd need to list schedules and match by name
            # For now, always create new schedule
            print(f"Creating schedule for {crawler_name}...")

            response = self._api_request('POST', 'schedules', payload)

            if response.status_code in [200, 201]:
                data = response.json()
                schedule_id = data.get('data', {}).get('id')
                print(f"✅ Schedule created/updated: {schedule_id}")
                return True
            else:
                print(f"❌ Failed to create schedule: {response.status_code}")
                print(f"   {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error syncing schedule: {e}")
            return False

    def sync_all_schedules(self, dry_run: bool = False):
        """Sync all schedules to Apify platform"""
        schedules = self.config.get('schedules', {})

        print(f"\n{'🔍 DRY RUN: ' if dry_run else ''}Syncing {len(schedules)} schedules...\n")

        success_count = 0
        for name in schedules.keys():
            if self.sync_schedule(name, dry_run):
                success_count += 1

        print(f"\n{'Would sync' if dry_run else 'Synced'} {success_count}/{len(schedules)} schedules")

    def validate_all(self):
        """Validate all schedule configurations"""
        schedules = self.config.get('schedules', {})

        print(f"Validating {len(schedules)} schedules...\n")

        all_valid = True
        for name in schedules.keys():
            config = self._get_schedule_config(name)
            if self._validate_schedule(name, config):
                print(f"✅ {name}")
            else:
                all_valid = False

        if all_valid:
            print("\n✅ All schedule configurations are valid")
        else:
            print("\n❌ Some schedules have validation errors")
            sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Sync Apify crawler schedules from YAML to Apify platform'
    )
    parser.add_argument(
        'command',
        choices=['list', 'show', 'validate', 'sync'],
        help='Command to run'
    )
    parser.add_argument(
        '--crawler', '-c',
        help='Crawler name (for show/sync commands)'
    )
    parser.add_argument(
        '--config',
        default='apify/crawler_schedules.yaml',
        help='Path to crawler_schedules.yaml'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be synced without making changes'
    )
    parser.add_argument(
        '--api-token',
        help='Apify API token (or set APIFY_API_TOKEN env var)'
    )

    args = parser.parse_args()

    # Construct config path
    config_path = Path(__file__).parent.parent / args.config

    try:
        manager = ApifyScheduleManager(config_path, args.api_token)

        if args.command == 'list':
            manager.list_schedules()

        elif args.command == 'show':
            if not args.crawler:
                print("Error: --crawler required for 'show' command")
                sys.exit(1)
            manager.show_schedule(args.crawler)

        elif args.command == 'validate':
            manager.validate_all()

        elif args.command == 'sync':
            if args.crawler:
                # Sync single crawler
                manager.sync_schedule(args.crawler, args.dry_run)
            else:
                # Sync all crawlers
                manager.sync_all_schedules(args.dry_run)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
