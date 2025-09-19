from dinopass_generator import DinoPassAnalyzer
import sys
import os
from itertools import product
import re

class CartesianGenerator(DinoPassAnalyzer):
    def __init__(self):
        # Call parent constructor to initialize all attributes
        super().__init__()
        
        # Extract leet characters from parent's mappings
        self.numeric_leet_chars = set()
        self.symbol_leet_chars = set()
        
        # Build sets from the parent's leetspeak_map
        for letter, substitutions in self.leetspeak_map.items():
            if not isinstance(substitutions, list):
                substitutions = [substitutions]
            
            for sub in substitutions:
                if sub.isdigit():
                    self.numeric_leet_chars.add(sub)
                else:
                    self.symbol_leet_chars.add(sub)
        
        # Also include common numeric leet not in the main map
        self.numeric_leet_chars.update({'0', '1', '2', '4', '5', '6', '7', '8', '9'})
        
        print(f"Initialized with numeric leet chars: {sorted(self.numeric_leet_chars)}")
        print(f"Initialized with symbol leet chars: {sorted(self.symbol_leet_chars)}")
    
    def has_leet_substitutions(self, text):
        """
        Check if text contains any leet speak substitutions.
        Returns (has_numeric_leet, has_symbol_leet, leet_chars_found)
        """
        # Remove the 2-digit suffix to focus on the word part
        word_part = re.sub(r'\d{2}$', '', text)
        
        # Find all non-alphabetic characters in the word part
        non_alpha_chars = set(re.findall(r'[^a-zA-Z]', word_part))
        
        # Categorize leet characters
        numeric_leet_found = non_alpha_chars.intersection(self.numeric_leet_chars)
        symbol_leet_found = non_alpha_chars.intersection(self.symbol_leet_chars)
        
        # Any other numeric characters (not in our leet set) are also considered numeric leet
        other_numeric = set(c for c in non_alpha_chars if c.isdigit() and c not in self.numeric_leet_chars)
        if other_numeric:
            numeric_leet_found.update(other_numeric)
        
        has_numeric = len(numeric_leet_found) > 0
        has_symbol = len(symbol_leet_found) > 0
        
        return has_numeric, has_symbol, non_alpha_chars

    def is_valid_leet_combination(self, text):
        """
        Check if the text contains EXACTLY ONE type of leet substitution:
        - Either only numeric leet (0-9) 
        - OR only symbol leet (non-alphanumeric except 0-9)
        - NOT mixed types
        - MUST have at least one leet substitution (never base + base)
        
        Returns True if valid, False if invalid (mixed types or no leet)
        """
        has_numeric, has_symbol, leet_chars = self.has_leet_substitutions(text)
        
        # Must have at least one type of leet (never base + base)
        if not has_numeric and not has_symbol:
            return False
        
        # Valid if we have ONLY numeric leet OR ONLY symbol leet, but not both
        return (has_numeric and not has_symbol) or (has_symbol and not has_numeric)

    def process_candidate(self, candidate: str, seen: set, out_f, total_written: int, 
                          rejected_mixed: int, dedupe=True, preview=0, label=""):
        """
        Helper function to handle candidate password processing:
        - Validate leet type consistency
        - Deduplicate
        - Write to file
        - Print preview if requested
        Returns updated (total_written, rejected_mixed)
        """
        if not self.is_valid_leet_combination(candidate):
            rejected_mixed += 1
            return total_written, rejected_mixed

        if dedupe and candidate in seen:
            return total_written, rejected_mixed

        seen.add(candidate)
        out_f.write(candidate + "\n")
        total_written += 1

        if preview and total_written <= preview:
            print(f"{label}: {candidate}")

        return total_written, rejected_mixed

    def get_word_variations(self, word, is_adjective=True):
        """
        Get all valid variations of a word (base + leet variants).
        Returns dict with 'base', 'numeric_leet', and 'symbol_leet' lists.
        """
        variations = {
            'base': [],
            'numeric_leet': [],
            'symbol_leet': []
        }
        
        # Base form
        if is_adjective:
            variations['base'].append(word.lower())
        else:
            variations['base'].append(word.capitalize())
        
        # Get all leet transformations
        leet_variants = self.apply_leet_transformations(word)
        
        for variant in leet_variants:
            if variant == word:  # Skip if same as original
                continue
                
            # Apply proper capitalization
            if is_adjective:
                variant = variant.lower()
            # For nouns, keep the capitalization from leet transformation
            
            # Categorize the variant
            has_numeric, has_symbol, _ = self.has_leet_substitutions(variant + "00")  # Add dummy suffix for testing
            
            if has_numeric and not has_symbol:
                variations['numeric_leet'].append(variant)
            elif has_symbol and not has_numeric:
                variations['symbol_leet'].append(variant)
            # Skip mixed variants
        
        return variations

    def generate_comprehensive_wordlist(self,
                                       output_file="dinopass_comprehensive.txt",
                                       digits_range=range(100),
                                       min_length=7,
                                       max_length=15,
                                       max_results=None,
                                       dedupe=True,
                                       preview=0,
                                       include_base_forms=True,
                                       include_leet_variants=True):
        """
        Generate a comprehensive wordlist that includes:
        1. Base forms: adjective + noun + digits (e.g., "wildLion42")
        2. Pure numeric leet variations
        3. Pure symbol leet variations
        4. NO mixed leet variations
        """
        if not self.adjectives or not self.nouns:
            print("Error: No adjectives or nouns loaded. Please run data collection first.")
            return 0

        seen = set()
        total_written = 0
        rejected_mixed = 0

        print(f"Generating comprehensive wordlist with {len(self.adjectives)} adjectives and {len(self.nouns)} nouns...")
        
        # Pre-calculate all valid variations
        print("Pre-calculating adjective variations...")
        adj_variations_map = {}
        for adj in sorted(self.adjectives):
            adj_variations_map[adj] = self.get_word_variations(adj, is_adjective=True)

        print("Pre-calculating noun variations...")
        noun_variations_map = {}
        for noun in sorted(self.nouns):
            noun_variations_map[noun] = self.get_word_variations(noun, is_adjective=False)

        # Calculate total combinations
        total_combinations = 0
        for adj_vars in adj_variations_map.values():
            for noun_vars in noun_variations_map.values():
                for adj_type in ['base', 'numeric_leet', 'symbol_leet']:
                    for noun_type in ['base', 'numeric_leet', 'symbol_leet']:
                        # Skip invalid combinations (both have same leet type)
                        if adj_type != 'base' and noun_type != 'base' and adj_type == noun_type:
                            continue
                        # Skip mixed leet types (one numeric, other symbol)
                        if (adj_type == 'numeric_leet' and noun_type == 'symbol_leet') or \
                           (adj_type == 'symbol_leet' and noun_type == 'numeric_leet'):
                            continue
                        
                        total_combinations += len(adj_vars[adj_type]) * len(noun_vars[noun_type]) * len(digits_range)
        
        print(f"Estimated valid combinations: {total_combinations:,}")
        print(f"Starting generation to {output_file}...")

        with open(output_file, "w") as out_f:
            adj_count = 0
            
            for base_adj in sorted(self.adjectives):
                adj_count += 1
                adj_variations = adj_variations_map[base_adj]
                
                for base_noun in sorted(self.nouns):
                    noun_variations = noun_variations_map[base_noun]
                    
                    # Generate all valid combinations (NO base + base)
                    valid_combinations = [
                        ('base', 'numeric_leet'),   # normal + numeric leet
                        ('base', 'symbol_leet'),    # normal + symbol leet  
                        ('numeric_leet', 'base'),   # numeric leet + normal
                        ('symbol_leet', 'base'),    # symbol leet + normal
                    ]
                    
                    for adj_type, noun_type in valid_combinations:
                        for adj_var in adj_variations[adj_type]:
                            for noun_var in noun_variations[noun_type]:
                                core = f"{adj_var}{noun_var}"
                                
                                for n in digits_range:
                                    digits = f"{n:02d}"
                                    candidate = f"{core}{digits}"
                                    total_len = len(candidate)

                                    if total_len > max_length or total_len < min_length:
                                        continue

                                    total_written, rejected_mixed = self.process_candidate(
                                        candidate, seen, out_f, total_written, rejected_mixed, 
                                        dedupe, preview, label=f"{adj_type}+{noun_type}"
                                    )

                                    if max_results and total_written >= max_results:
                                        print(f"Stopped early at {total_written} passwords")
                                        print(f"Rejected {rejected_mixed} invalid combinations")
                                        return total_written

                                    if total_written % 100000 == 0 and total_written > 0:
                                        print(f"Generated {total_written:,} passwords...")
                
                if adj_count % 5 == 0:
                    progress = adj_count / len(self.adjectives) * 100
                    print(f"Progress: {progress:.1f}% ({adj_count}/{len(self.adjectives)} adjectives)")

        print(f"Done — wrote {total_written:,} unique passwords to {output_file}")
        print(f"Rejected {rejected_mixed} invalid combinations")
        return total_written

    def generate_cartesian_with_rules(self,
                                      output_file="dinopass_cartesian.txt",
                                      digits_range=range(100),
                                      min_length=7,
                                      max_length=12,
                                      max_results=None,
                                      dedupe=True,
                                      preview=0):
        """
        Generate Cartesian product with strict validation:
        - Base forms (no leet)
        - Pure numeric leet (either adjective OR noun, not both)
        - Pure symbol leet (either adjective OR noun, not both)
        - NO mixed numeric/symbol combinations
        """
        if not self.adjectives or not self.nouns:
            print("Error: No adjectives or nouns loaded. Please run data collection first.")
            return 0

        seen = set()
        total_written = 0
        rejected_mixed = 0

        print(f"Generating rule-compliant wordlist with {len(self.adjectives)} adjectives and {len(self.nouns)} nouns...")
        print("Enforcing: NO mixed leet types (numeric and symbol together)")
        
        with open(output_file, "w") as out_f:
            adj_count = 0
            
            for base_adj in sorted(self.adjectives):
                adj_count += 1
                
                # Get all variations for this adjective
                adj_variations = self.get_word_variations(base_adj, is_adjective=True)
                
                for base_noun in sorted(self.nouns):
                    # Get all variations for this noun
                    noun_variations = self.get_word_variations(base_noun, is_adjective=False)
                    
                    # Generate valid combinations only (NO base + base)
                    valid_pairs = []
                    
                    # Base + Numeric leet
                    for adj in adj_variations['base']:
                        for noun in noun_variations['numeric_leet']:
                            valid_pairs.append((adj, noun, "base+numeric"))
                    
                    # Base + Symbol leet  
                    for adj in adj_variations['base']:
                        for noun in noun_variations['symbol_leet']:
                            valid_pairs.append((adj, noun, "base+symbol"))
                    
                    # Numeric leet + Base
                    for adj in adj_variations['numeric_leet']:
                        for noun in noun_variations['base']:
                            valid_pairs.append((adj, noun, "numeric+base"))
                    
                    # Symbol leet + Base
                    for adj in adj_variations['symbol_leet']:
                        for noun in noun_variations['base']:
                            valid_pairs.append((adj, noun, "symbol+base"))
                    
                    # Generate passwords from valid pairs
                    for adj_var, noun_var, combo_type in valid_pairs:
                        core = f"{adj_var}{noun_var}"
                        
                        for n in digits_range:
                            digits = f"{n:02d}"
                            candidate = f"{core}{digits}"
                            
                            if len(candidate) < min_length or len(candidate) > max_length:
                                continue

                            total_written, rejected_mixed = self.process_candidate(
                                candidate, seen, out_f, total_written, rejected_mixed, 
                                dedupe, preview, label=combo_type
                            )

                            if max_results and total_written >= max_results:
                                print(f"Stopped early at {total_written} passwords")
                                print(f"Rejected {rejected_mixed} invalid combinations")
                                return total_written
                
                if adj_count % 5 == 0:
                    progress = adj_count / len(self.adjectives) * 100
                    print(f"Progress: {progress:.1f}% ({adj_count}/{len(self.adjectives)} adjectives)")
                    
        print(f"Done — wrote {total_written:,} unique passwords to {output_file}")
        print(f"Rejected {rejected_mixed} invalid combinations")
        return total_written

    def test_leet_validation(self):
        """
        Test the leet validation logic with example passwords.
        """
        test_cases = [
            # Valid cases - always has leet
            ("w1ldLion42", True, "numeric leet adj only"),
            ("wildL10n42", True, "numeric leet noun only"),
            ("w!ldLion42", True, "symbol leet adj only"),
            ("wildL!on42", True, "symbol leet noun only"),
            ("wild7iger99", True, "numeric leet noun only"),
            ("br@veEagle23", True, "symbol leet adj only"),
            
            # Invalid cases - no leet at all
            ("wildLion42", False, "base form - no leet"),
            ("gentleTiger99", False, "base form - no leet"),
            
            # Invalid cases - mixed leet types
            ("w1ldL!on42", False, "mixed: numeric adj + symbol noun"),
            ("w!ldL10n42", False, "mixed: symbol adj + numeric noun"),
            ("w1ld7!ger42", False, "mixed: numeric and symbol in noun"),
            ("w!1dLion42", False, "mixed: symbol and numeric in adj"),
        ]
        
        print("Testing leet validation logic:")
        print("=" * 50)
        
        all_passed = True
        for password, expected, description in test_cases:
            result = self.is_valid_leet_combination(password)
            status = "✓" if result == expected else "✗"
            
            if result != expected:
                all_passed = False
            
            has_numeric, has_symbol, leet_chars = self.has_leet_substitutions(password)
            leet_info = f"(num:{has_numeric}, sym:{has_symbol})"
            
            print(f"{status} {password:<15} | {description:<25} | Expected: {expected}, Got: {result} {leet_info}")
        
        print("=" * 50)
        if all_passed:
            print("✓ All tests passed!")
        else:
            print("✗ Some tests failed!")
        
        return all_passed

    def analyze_coverage(self, sample_passwords=None):
        """
        Analyze what percentage of actual DinoPass passwords would be covered
        by our wordlist generation.
        """
        if sample_passwords is None:
            print("Fetching sample passwords for coverage analysis...")
            sample_passwords = self.fetch_passwords_threaded(200, max_workers=5)
        
        print(f"Analyzing coverage with {len(sample_passwords)} sample passwords...")
        
        # Analyze the sample passwords first
        print("\nSample password analysis:")
        valid_count = 0
        invalid_count = 0
        
        for pwd in sample_passwords[:20]:  # Show first 20 as examples
            is_valid = self.is_valid_leet_combination(pwd)
            has_numeric, has_symbol, leet_chars = self.has_leet_substitutions(pwd)
            
            if is_valid:
                valid_count += 1
                print(f"✓ {pwd} (num:{has_numeric}, sym:{has_symbol})")
            else:
                invalid_count += 1
                print(f"✗ {pwd} (num:{has_numeric}, sym:{has_symbol}) - MIXED LEET")
        
        # Count all
        for pwd in sample_passwords[20:]:
            if self.is_valid_leet_combination(pwd):
                valid_count += 1
            else:
                invalid_count += 1
        
        print(f"\nValidation Summary:")
        print(f"Valid passwords: {valid_count}/{len(sample_passwords)} ({valid_count/len(sample_passwords)*100:.1f}%)")
        print(f"Invalid (mixed leet): {invalid_count}/{len(sample_passwords)} ({invalid_count/len(sample_passwords)*100:.1f}%)")
        
        return valid_count / len(sample_passwords) * 100

    def ensure_components_loaded(self):
        """
        Ensure we have adjectives and nouns loaded, either from files or by fetching new data.
        """
        # Try to load from files first
        if self.load_components():
            return True
            
        print("Component files not found. Would you like to:")
        print("1. Fetch new passwords to build components")
        print("2. Exit and run the main generator first")
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            print("Fetching passwords to build component lists...")
            passwords = self.fetch_passwords_threaded(1000, max_workers=10)
            self.analyze_corpus(passwords)
            
            if self.adjectives and self.nouns:
                self.save_components()
                print("Components saved for future use.")
                return True
            else:
                print("Failed to extract components from fetched passwords.")
                return False
        else:
            print("Please run the main dinopass_generator.py first to collect data.")
            return False


# Test function for standalone running
if __name__ == "__main__":
    generator = CartesianGenerator()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        generator.test_leet_validation()
    else:
        print("Use 'python cartesian_rule.py test' to test validation logic")
        print("Or import this module into your main generator")