#!/usr/bin/env python3
"""
Manage Apify crawler configurations
- Read crawler_config.yaml
- Validate settings
- Display configurations
- Generate deployment commands
"""

import sys
from pathlib import Path
from typing import Dict, Any

try:
    import yaml
except ImportError:
    print("Error: pyyaml not installed. Run: pip install pyyaml")
    sys.exit(1)


class CrawlerConfigManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load crawler configuration from YAML"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_crawler_config(self, crawler_name: str) -> Dict[str, Any]:
        """Get full configuration for a crawler (defaults + overrides)"""
        defaults = self.config.get('defaults', {})
        crawler_config = self.config.get('crawlers', {}).get(crawler_name, {})
        
        # Merge defaults with crawler-specific config
        config = defaults.copy()
        config.update(crawler_config)
        
        return config
    
    def validate_config(self, crawler_name: str) -> bool:
        """Validate crawler configuration"""
        config = self.get_crawler_config(crawler_name)
        
        errors = []
        
        # Validate memory
        memory = config.get('memory_mbytes', 0)
        if memory <= 0:
            errors.append(f"memory_mbytes must be > 0, got {memory}")
        
        # Validate rate limits
        rate_limit = config.get('max_requests_per_minute', 0)
        if rate_limit <= 0:
            errors.append(f"max_requests_per_minute must be > 0, got {rate_limit}")
        
        # Validate timeout
        timeout = config.get('request_handler_timeout_secs', 0)
        if timeout <= 0:
            errors.append(f"request_handler_timeout_secs must be > 0, got {timeout}")
        
        # Validate concurrency
        min_conc = config.get('min_concurrency', 0)
        max_conc = config.get('max_concurrency', 0)
        if min_conc < 0 or max_conc < 0:
            errors.append(f"Concurrency must be >= 0")
        if min_conc > max_conc:
            errors.append(f"min_concurrency ({min_conc}) > max_concurrency ({max_conc})")
        
        if errors:
            print(f"❌ Validation errors for {crawler_name}:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    def list_crawlers(self):
        """List all configured crawlers with their settings"""
        print("\n=== Apify Crawler Configurations ===\n")
        
        crawlers = self.config.get('crawlers', {})
        
        for name, crawler_config in crawlers.items():
            config = self.get_crawler_config(name)
            
            print(f"📦 {name}")
            print(f"   Name: {config.get('name', 'N/A')}")
            print(f"   Title: {config.get('title', 'N/A')}")
            print(f"   Memory: {config.get('memory_mbytes', 'N/A')} MB")
            print(f"   Rate Limit: {config.get('max_requests_per_minute', 'N/A')} req/min")
            print(f"   Timeout: {config.get('request_handler_timeout_secs', 'N/A')}s")
            print(f"   Concurrency: {config.get('min_concurrency', 'N/A')}-{config.get('max_concurrency', 'N/A')}")
            
            schedule = crawler_config.get('schedule', {})
            if schedule.get('enabled'):
                print(f"   Schedule: {schedule.get('cron', 'N/A')} ({schedule.get('timezone', 'N/A')})")
            
            print()
        
    def show_crawler(self, crawler_name: str):
        """Show detailed configuration for a specific crawler"""
        if crawler_name not in self.config.get('crawlers', {}):
            print(f"❌ Crawler '{crawler_name}' not found")
            return
        
        config = self.get_crawler_config(crawler_name)
        
        print(f"\n=== {crawler_name} Configuration ===\n")
        print(yaml.dump(config, default_flow_style=False, sort_keys=False))
        
        # Validate
        if self.validate_config(crawler_name):
            print("✅ Configuration is valid")
        
    def generate_apify_command(self, crawler_name: str):
        """Generate apify command for deployment"""
        if crawler_name not in self.config.get('crawlers', {}):
            print(f"❌ Crawler '{crawler_name}' not found")
            return
        
        config = self.get_crawler_config(crawler_name)
        crawler_config = self.config.get('crawlers', {}).get(crawler_name, {})
        
        actor_name = config.get('name', '')
        default_input = crawler_config.get('default_input', {})
        memory = config.get('memory_mbytes', 1024)
        
        print(f"\n=== Apify Deployment Commands for {crawler_name} ===\n")
        
        # Push command
        print(f"# Deploy to Apify")
        print(f"cd apify/{crawler_name}-crawler")
        print(f"apify push\n")
        
        # Run command
        print(f"# Run with default input")
        print(f"apify actor call {actor_name} \\")
        print(f"  --input '{yaml.dump(default_input, default_flow_style=True).strip()}' \\")
        print(f"  --memory-mbytes {memory}\n")
        
        # Schedule (if configured)
        schedule = crawler_config.get('schedule', {})
        if schedule.get('enabled'):
            print(f"# Schedule configuration")
            print(f"Cron: {schedule.get('cron')}")
            print(f"Timezone: {schedule.get('timezone')}")
            print(f"Memory: {memory} MB")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage Apify crawler configurations')
    parser.add_argument('command', choices=['list', 'show', 'validate', 'deploy'],
                       help='Command to run')
    parser.add_argument('--crawler', '-c', help='Crawler name')
    parser.add_argument('--config', default='apify/crawler_config.yaml',
                       help='Path to crawler_config.yaml')
    
    args = parser.parse_args()
    
    # Construct config path
    config_path = Path(__file__).parent.parent / args.config
    
    try:
        manager = CrawlerConfigManager(config_path)
        
        if args.command == 'list':
            manager.list_crawlers()
        
        elif args.command == 'show':
            if not args.crawler:
                print("Error: --crawler required for 'show' command")
                sys.exit(1)
            manager.show_crawler(args.crawler)
        
        elif args.command == 'validate':
            if args.crawler:
                # Validate single crawler
                if manager.validate_config(args.crawler):
                    print(f"✅ {args.crawler} configuration is valid")
            else:
                # Validate all crawlers
                print("Validating all crawlers...\n")
                all_valid = True
                for crawler_name in manager.config.get('crawlers', {}).keys():
                    if manager.validate_config(crawler_name):
                        print(f"✅ {crawler_name}")
                    else:
                        all_valid = False
                
                if all_valid:
                    print("\n✅ All configurations are valid")
                else:
                    print("\n❌ Some configurations have errors")
                    sys.exit(1)
        
        elif args.command == 'deploy':
            if not args.crawler:
                print("Error: --crawler required for 'deploy' command")
                sys.exit(1)
            manager.generate_apify_command(args.crawler)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
