#!/usr/bin/env python3
"""
DinoPass Accuracy Testing Suite
Fetches 10,000 passwords from dinopass.com/password/strong and checks coverage
against the generated wordlist file.
"""

import requests
import time
from concurrent.futures import ThreadPoolExecutor
import queue
import sys

class DinoPassTester:
    def __init__(self, wordlist_file="dinopass_cartesian.txt"):
        self.wordlist_file = wordlist_file
        self.url = "http://www.dinopass.com/password/strong"
        self.generated_passwords = set()
        
    def load_wordlist(self):
        """Load the generated wordlist into memory"""
        print(f"Loading wordlist from {self.wordlist_file}...")
        try:
            with open(self.wordlist_file, 'r') as f:
                self.generated_passwords = set(line.strip() for line in f if line.strip())
            print(f"Loaded {len(self.generated_passwords):,} passwords from wordlist")
            return True
        except FileNotFoundError:
            print(f"Error: Wordlist file '{self.wordlist_file}' not found!")
            return False
        except Exception as e:
            print(f"Error loading wordlist: {e}")
            return False
    
    def fetch_dinopass_sample(self, sample_size=10000, max_workers=20):
        """
        Fetch sample passwords from DinoPass using multiple threads
        """
        print(f"Fetching {sample_size:,} passwords from DinoPass...")
        passwords = []
        password_queue = queue.Queue()
        failed_requests = 0

        def fetch_single_password():
            nonlocal failed_requests
            try:
                response = requests.get(self.url, timeout=10)
                if response.status_code == 200:
                    password_queue.put(response.text.strip())
                else:
                    password_queue.put(None)
                    failed_requests += 1
            except requests.RequestException:
                password_queue.put(None)
                failed_requests += 1

        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(fetch_single_password) for _ in range(sample_size)]
            
            collected = 0
            while collected < sample_size:
                try:
                    password = password_queue.get(timeout=60)
                    if password:
                        passwords.append(password)
                    collected += 1
                    
                    # Progress update every 500 requests
                    if collected % 500 == 0:
                        success_rate = len(passwords) / collected * 100
                        print(f"Progress: {collected:,}/{sample_size:,} requests completed "
                              f"({success_rate:.1f}% success rate)")
                        
                except queue.Empty:
                    print("Timeout waiting for passwords")
                    break

        print(f"Successfully collected {len(passwords):,} valid passwords")
        print(f"Failed requests: {failed_requests:,}")
        return passwords
    
    def test_coverage(self, sample_passwords):
        """
        Test what percentage of DinoPass passwords are covered by our wordlist
        """
        print(f"\nTesting coverage against {len(sample_passwords):,} DinoPass samples...")
        
        matches = []
        misses = []
        
        for password in sample_passwords:
            if password in self.generated_passwords:
                matches.append(password)
            else:
                misses.append(password)
        
        # Calculate statistics
        total_samples = len(sample_passwords)
        match_count = len(matches)
        miss_count = len(misses)
        coverage_percentage = (match_count / total_samples * 100) if total_samples > 0 else 0
        
        # Print results
        print(f"\n" + "="*60)
        print(f"COVERAGE TEST RESULTS")
        print(f"="*60)
        print(f"Total DinoPass samples:     {total_samples:,}")
        print(f"Found in wordlist:          {match_count:,}")
        print(f"Missing from wordlist:      {miss_count:,}")
        print(f"Coverage accuracy:          {coverage_percentage:.2f}%")
        print(f"="*60)
        
        return {
            'total_samples': total_samples,
            'matches': match_count,
            'misses': miss_count,
            'coverage_percentage': coverage_percentage,
            'missing_passwords': misses[:100]  # Return first 100 missing passwords
        }
    
    def analyze_missing_passwords(self, missing_passwords):
        """
        Analyze the patterns in missing passwords to understand gaps
        """
        if not missing_passwords:
            print("\n✅ Perfect coverage! No missing passwords found.")
            return
        
        print(f"\n🔍 ANALYZING {len(missing_passwords)} MISSING PASSWORDS:")
        print("-" * 50)
        
        # Show first 20 missing passwords
        print("First 20 missing passwords:")
        for i, password in enumerate(missing_passwords[:20]):
            print(f"  {i+1:2d}. {password}")
        
        if len(missing_passwords) > 20:
            print(f"     ... and {len(missing_passwords) - 20} more")
        
        # Analyze patterns
        patterns = {
            'too_short': 0,
            'too_long': 0,
            'no_leet': 0,
            'multiple_leet': 0,
            'mixed_leet': 0,
            'parsing_issues': 0
        }
        
        numeric_leet = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
        
        for password in missing_passwords[:100]:  # Analyze first 100
            if len(password) < 7:
                patterns['too_short'] += 1
            elif len(password) > 15:
                patterns['too_long'] += 1
            else:
                # Analyze leet content
                core = password[:-2] if len(password) >= 2 else password
                leet_chars = [c for c in core if not c.isalnum()]
                
                if len(leet_chars) == 0:
                    patterns['no_leet'] += 1
                elif len(leet_chars) > 1:
                    patterns['multiple_leet'] += 1
                elif len(leet_chars) == 1:
                    # Check for mixed types (shouldn't happen with 1 char, but just in case)
                    numeric_count = sum(1 for c in leet_chars if c in numeric_leet)
                    symbol_count = len(leet_chars) - numeric_count
                    if numeric_count > 0 and symbol_count > 0:
                        patterns['mixed_leet'] += 1
                    else:
                        patterns['parsing_issues'] += 1
        
        print(f"\nPattern analysis of missing passwords:")
        for pattern, count in patterns.items():
            if count > 0:
                print(f"  {pattern.replace('_', ' ').title()}: {count}")
    
    def run_full_test(self, sample_size=10000):
        """
        Run the complete testing suite
        """
        print("🔧 DinoPass Wordlist Coverage Test")
        print("=" * 50)
        
        # Step 1: Load wordlist
        if not self.load_wordlist():
            return False
        
        # Step 2: Fetch DinoPass samples
        sample_passwords = self.fetch_dinopass_sample(sample_size)
        if not sample_passwords:
            print("Failed to fetch DinoPass samples!")
            return False
        
        # Step 3: Test coverage
        results = self.test_coverage(sample_passwords)
        
        # Step 4: Analyze missing passwords
        self.analyze_missing_passwords(results['missing_passwords'])
        
        # Step 5: Summary
        print(f"\n📊 FINAL SUMMARY:")
        print(f"   Wordlist size: {len(self.generated_passwords):,} passwords")
        print(f"   Coverage: {results['coverage_percentage']:.2f}%")
        
        if results['coverage_percentage'] >= 95:
            print("   🎉 Excellent coverage!")
        elif results['coverage_percentage'] >= 85:
            print("   ✅ Good coverage")
        elif results['coverage_percentage'] >= 70:
            print("   ⚠️  Moderate coverage - consider improvements")
        else:
            print("   ❌ Low coverage - significant gaps exist")
        
        return results

def main():
    """Main function to run the test"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test DinoPass wordlist coverage")
    parser.add_argument("--wordlist", "-w", default="dinopass_cartesian.txt", 
                       help="Path to the generated wordlist file")
    parser.add_argument("--samples", "-s", type=int, default=10000,
                       help="Number of DinoPass samples to test (default: 10000)")
    
    args = parser.parse_args()
    
    tester = DinoPassTester(args.wordlist)
    results = tester.run_full_test(args.samples)
    
    if results:
        # Return non-zero exit code if coverage is poor
        if results['coverage_percentage'] < 80:
            sys.exit(1)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()