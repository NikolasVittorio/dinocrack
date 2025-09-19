#!/usr/bin/env python3
"""
DinoPass Password Pattern Generator - Simplified digit handling

Changes:
- Always strips the final 2 characters for analysis (the user indicated the
  final two characters are not important and can be removed).
- Single, consistent validate_patterns implementation (removed duplicate).
- More robust, case-insensitive "deleet" (leet -> normal) conversion.
- Simpler, reliable split for camelCase (split at first internal uppercase).
- Fallback split strategies for non-camelCase tokens.
- Added --test-examples to quickly check the sample cases.
"""

import requests
from concurrent.futures import ThreadPoolExecutor
import queue
from spellchecker import SpellChecker
import re



class DinoPassAnalyzer:
    def __init__(self):
        self.url = "http://www.dinopass.com/password/strong"
        self.adjectives = set()
        self.nouns = set()
        self.leetspeak_map = {
            'a': '@',
            'c': ['(', '<'],
            'k': '<',
            'e': '3',
            't': '+',
            'i': '!',
            'd': [')', '>'],
            's': '$',
            'f': '=',
            'j': ']',
            'l': '['
        }
        # Reverse mapping for deleet (symbols -> normal letter)
        self.spell = SpellChecker()
        self.reverse_leet_map = {
            '@': ['a'],
            '(': ['c'],
            '<': ['c', 'k'],  # multiple options trigger spellcheck
            '3': ['e'],
            '+': ['t'],
            '!': ['i'],
            ')': ['d'],
            '>': ['d'],
            '$': ['s'],
            '=': ['f'],
            ']': ['j'], 
            '2': ['z'],
            '[': ['l']
        }

        self.password_patterns = []
        # --- Helper import ---
        from saturated_fetch import fetch_until_saturation
        DinoPassAnalyzer.fetch_until_saturation = fetch_until_saturation

    def fetch_passwords_threaded(self, count=1000, max_workers=10):
        """
        Fetch passwords using multiple threads for speed
        """
        print(f"Fetching {count} passwords from DinoPass using {max_workers} threads...")
        passwords = []
        password_queue = queue.Queue()

        def fetch_single_password():
            try:
                response = requests.get(self.url, timeout=5)
                if response.status_code == 200:
                    password_queue.put(response.text.strip())
                else:
                    password_queue.put(None)
            except requests.RequestException:
                password_queue.put(None)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(fetch_single_password) for _ in range(count)]

            collected = 0
            while collected < count:
                try:
                    p = password_queue.get(timeout=30)
                    if p:
                        passwords.append(p)
                    collected += 1
                    if collected % 50 == 0:
                        print(f"Progress: {collected}/{count} requests completed")
                except queue.Empty:
                    print("Timeout waiting for passwords")
                    break

        print(f"Successfully collected {len(passwords)} valid passwords")
        return passwords

    def deleet_word(self, word):
        """
        Convert leet-speak-like characters back to normal characters.
        Only apply spell-checking for characters that have multiple possible substitutions.
        """
        candidates = {word.lower()}

        # Track if multiple substitutions exist in this word
        apply_spellcheck = any(ch in word for ch, normals in self.reverse_leet_map.items() if len(normals) > 1)

        for leet, normals in self.reverse_leet_map.items():
            if not isinstance(normals, list):
                normals = [normals]
            new_candidates = set()
            for cand in candidates:
                if leet in cand:
                    for n in normals:
                        new_candidates.add(cand.replace(leet, n))
                else:
                    new_candidates.add(cand)
            candidates = new_candidates

        # Remove non-letter characters
        candidates = {re.sub(r'[^a-z]', '', c) for c in candidates}

        if apply_spellcheck:
            # Only use spellcheck if there were ambiguous substitutions
            valid_candidates = [c for c in candidates if c in self.spell]
            if valid_candidates:
                return valid_candidates[0]

        # Fallback: return first candidate
        return next(iter(candidates)) if candidates else word

    def analyze_password_structure(self, password):
        """
        Analyze the structure of a password.

        Simplified digit handling:
        - We always remove the final TWO characters before attempting to split into adjective + noun.
          (the final two chars are not important and can be removed these being random numbers.)

        Splitting strategy:
        - Prefer splitting at the first internal uppercase (camelCase boundary).
        - If no uppercase boundary, try to split at a letter/non-letter boundary.
        - Fallback: split roughly in half (keeps reasonable minimum sizes).
        """
        if not password or len(password) < 4:
            return None

        # Always consider last two characters as the "suffix" to drop for analysis
        suffix = password[-2:]
        body = password[:-2]

        # Attempt 1: split at first internal uppercase (camelCase)
        parts = re.split(r'(?<!^)(?=[A-Z])', body, maxsplit=1)
        if len(parts) == 2:
            left, right = parts[0], parts[1]
        else:
            # Attempt 2: split at letter / non-letter boundary (e.g. 'ba)Blob' -> 'ba' + ')Blob')
            m = re.match(r'^([A-Za-z]+)([^A-Za-z].+)$', body)
            if m:
                left, right = m.group(1), m.group(2)
            else:
                # Fallback: split roughly in half but ensure at least 2 chars on each side
                mid = max(2, len(body) // 2)
                # if body short, bail out
                if mid >= len(body):
                    return None
                left, right = body[:mid], body[mid:]

        # De-leet each side individually and normalize to lowercase
        left_clean = self.deleet_word(left).lower()
        right_clean = self.deleet_word(right).lower()

        # Validate lengths
        if len(left_clean) < 2 or len(right_clean) < 2:
            return None

        # Ensure suffix is digits if possible; if not, keep it as is but mark empty digits
        digits = suffix if suffix.isdigit() else ''

        return {
            'adjective': left_clean,
            'noun': right_clean,
            'digits': digits,
            'original': password,
            'clean_form': f"{left_clean}{right_clean.capitalize()}{digits}"
        }

    def apply_leet_transformations(self, word):
        """
        Generate leet variations with EXACTLY ONE substitution per word.
        This ensures we get ]ade, ja]e, jad3 from jade, but not ]a]e or ]ad3.
        """
        if not word:
            return [word]
        
        word_lower = word.lower()
        variations = set()
        
        # Always include the original word (capitalized for nouns)
        if word and word[0].isalpha():
            variations.add(word[0].upper() + word[1:])
        else:
            variations.add(word)
        
        # Generate exactly one substitution variants
        for i, char in enumerate(word_lower):
            if char in self.leetspeak_map:
                leet_options = self.leetspeak_map[char]
                if not isinstance(leet_options, list):
                    leet_options = [leet_options]
                
                # For each possible leet substitution at position i
                for leet_char in leet_options:
                    # Create variant with only this one substitution
                    variant_chars = list(word_lower)
                    variant_chars[i] = leet_char
                    variant = ''.join(variant_chars)
                    
                    # Capitalize first letter if it's alphabetic (for nouns)
                    if variant and variant[0].isalpha():
                        variant = variant[0].upper() + variant[1:]
                    elif variant and not variant[0].isalpha():
                        # If first char is leet symbol, keep as-is
                        pass
                    
                    variations.add(variant)
        
        return sorted(list(variations))


    def analyze_corpus(self, passwords, append_mode=True):
        """
        Analyze all passwords to extract adjectives and nouns
        
        Parameters:
        - passwords: list of passwords to analyze
        - append_mode: if True, add to existing sets; if False, replace them
        """
        if not append_mode:
            # Reset everything if not in append mode
            self.adjectives.clear()
            self.nouns.clear()
            self.password_patterns.clear()
        
        print(f"Analyzing {len(passwords)} password patterns...")
        successful_analyses = 0
        failed_patterns = []
        
        # Track new discoveries for this batch
        initial_adj_count = len(self.adjectives)
        initial_noun_count = len(self.nouns)

        for password in passwords:
            analysis = self.analyze_password_structure(password)
            if analysis:
                # Track if this is a new adjective or noun
                is_new_adj = analysis['adjective'] not in self.adjectives
                is_new_noun = analysis['noun'] not in self.nouns
                
                self.adjectives.add(analysis['adjective'])
                self.nouns.add(analysis['noun'])
                self.password_patterns.append(analysis)
                successful_analyses += 1
                    
            else:
                failed_patterns.append(password)

        # Calculate actual new discoveries
        new_adj_count = len(self.adjectives) - initial_adj_count
        new_noun_count = len(self.nouns) - initial_noun_count

        print(f"Analysis complete:")
        print(f"  - Successfully analyzed: {successful_analyses}/{len(passwords)} passwords")
        print(f"  - New adjectives found: {new_adj_count}")
        print(f"  - New nouns found: {new_noun_count}")
        print(f"  - Total unique adjectives: {len(self.adjectives)}")
        print(f"  - Total unique nouns: {len(self.nouns)}")

        if failed_patterns and len(failed_patterns) < 20:
            print(f"  - Failed to parse (examples): {failed_patterns[:5]}")
        elif failed_patterns:
            print(f"  - Failed to parse: {len(failed_patterns)} passwords")

        return {
            'successful': successful_analyses,
            'failed': len(failed_patterns),
            'new_adjectives': new_adj_count,
            'new_nouns': new_noun_count
        }

    def generate_wordlist_fast(self, output_file="dinopass_wordlist.txt", max_combinations=None):
        """
        Fast wordlist generation with progress tracking (uses two-digit suffixes 00-99).
        """
        print("Generating comprehensive wordlist...")

        # Pre-calculate noun variations
        noun_variations_map = {}
        for noun in sorted(self.nouns):
            noun_variations_map[noun] = self.apply_leet_transformations(noun)

        total_possible = len(self.adjectives) * sum(len(vars) for vars in noun_variations_map.values()) * 100
        if max_combinations:
            total_possible = min(total_possible, max_combinations)

        print(f"Will generate up to {total_possible:,} combinations")

        with open(output_file, 'w') as f:
            count = 0

            for adj_idx, adjective in enumerate(sorted(self.adjectives)):
                if max_combinations and count >= max_combinations:
                    break

                for noun_idx, noun in enumerate(sorted(self.nouns)):
                    if max_combinations and count >= max_combinations:
                        break

                    noun_variations = noun_variations_map[noun]

                    for var_idx, noun_var in enumerate(noun_variations):
                        if max_combinations and count >= max_combinations:
                            break

                        for i in range(100):
                            if max_combinations and count >= max_combinations:
                                break

                            digits = f"{i:02d}"
                            password = f"{adjective}{noun_var}{digits}"
                            f.write(password + "\n")
                            count += 1

                if (adj_idx + 1) % 20 == 0:
                    progress = (adj_idx + 1) / max(1, len(self.adjectives)) * 100
                    print(f"Progress: {progress:.1f}% - Generated {count:,} combinations")

        print(f"Generated {count:,} password combinations")
        print(f"Wordlist saved to: {output_file}")

    def save_components(self, adj_file="adjectives.txt", noun_file="nouns.txt"):
        with open(adj_file, 'w') as f:
            for adj in sorted(self.adjectives):
                f.write(adj + "\n")

        with open(noun_file, 'w') as f:
            for noun in sorted(self.nouns):
                f.write(noun + "\n")

        print(f"Saved {len(self.adjectives)} adjectives to {adj_file}")
        print(f"Saved {len(self.nouns)} nouns to {noun_file}")

    def load_components(self, adj_file="adjectives.txt", noun_file="nouns.txt"):
        try:
            with open(adj_file, 'r') as f:
                self.adjectives = set(line.strip() for line in f if line.strip())
            with open(noun_file, 'r') as f:
                self.nouns = set(line.strip() for line in f if line.strip())
            print(f"Loaded {len(self.adjectives)} adjectives and {len(self.nouns)} nouns from files")
            return True
        except FileNotFoundError as e:
            print(f"Component files not found: {e}")
            return False

    def validate_patterns(self, sample_size=20):
        """
        Validate that our pattern recognition is working correctly.

        IMPORTANT: This uses the same "always drop last 2 chars" logic to
        reconstruct the cleaned token used during analysis.
        """
        print(f"\nValidating pattern recognition with {sample_size} samples:")
        print("-" * 60)

        for i, pattern in enumerate(self.password_patterns[:sample_size]):
            original = pattern['original']
            reconstructed = pattern['clean_form']
            print(f"{original:20} -> {pattern['adjective']:10} + {pattern['noun']:10} + {pattern['digits']}")
            # Reconstruct the cleaned word by removing last 2 characters from original
            clean_word_from_original = self.deleet_word(original[:-2])
            expected_clean = pattern['adjective'] + pattern['noun'].capitalize()

            if clean_word_from_original.lower() != expected_clean.lower():
                print(f"  âš ï¸  Potential mismatch: {clean_word_from_original} vs {expected_clean}")

def main():
    analyzer = DinoPassAnalyzer()

    # Attach saturation fetch if not already
    from saturated_fetch import fetch_until_saturation
    DinoPassAnalyzer.fetch_until_saturation = fetch_until_saturation

    while True:
        
        print("\033[0;32m" + r"""       
       ___                                  __             __
  ____/ (_)___  ____  ______________ ______/ /__          / _)
 / __  / / __ \/ __ \/ ___/ ___/ __ `/ ___/ //_/   .-^^^-/ /
/ /_/ / / / / / /_/ / /__/ /  / /_/ / /__/ ,<   __/       /
\__,_/_/_/ /_/\____/\___/_/   \__,_/\___/_/|_| <__.|_|-|_|

By NikolasVittorio

        """ + "\033[0m")

        print("--- DinoPass Password Analyzer ---")
        print("1. Fetch new passwords")
        print("2. Run comprehensive fetch until saturation")
        print("3. Generate wordlist")
        print("0. Exit")

        choice = input("Select an option (0-3): ").strip()

        if choice == "1":
            num = input("Enter number of passwords to fetch: ").strip()
            num = int(num) if num.isdigit() else 1000
            passwords = analyzer.fetch_passwords_threaded(num, max_workers=10)
            analyzer.analyze_corpus(passwords)
            analyzer.save_components()

        elif choice == "2":
            target = input("Enter target samples for saturation (default 5000): ").strip()
            target = int(target) if target.isdigit() else 5000
            analyzer.fetch_until_saturation(target_samples=target, batch_size=500, threads=10)
            analyzer.save_components()

        elif choice == "3":
            if not analyzer.load_components():
                print("No components loaded. Please fetch passwords first (option 1 or 2).")
                continue

            try:
                import sys
                import os

                
                script_dir = os.path.dirname(os.path.abspath(__file__))
                if script_dir not in sys.path:
                    sys.path.insert(0, script_dir)

                from cartesian_rule import CartesianGenerator

                print("\n--- Cartesian Rules Wordlist Generator ---")
                output_file = input("Output filename (default: dinopass_strong_pass.txt): ").strip()
                output_file = output_file or "dinopass_strong_pass.txt"

                # Create CartesianGenerator with loaded data
                cart_gen = CartesianGenerator()
                cart_gen.adjectives = analyzer.adjectives
                cart_gen.nouns = analyzer.nouns

                print("Generating Cartesian rules wordlist with default parameters...")
                print("Rules: exactly one substitution, length 7-12, adjective+noun+digits format")

                total = cart_gen.generate_comprehensive_wordlist(
                    output_file=output_file,
                    preview=20  # Show first 20 passwords as preview
                )
                print(f"Cartesian generation complete! Generated {total:,} passwords.")

            except ImportError:
                print("Error: cartesian_rule.py not found. Please ensure the file is in the same directory.")
            except KeyboardInterrupt:
                print("\nGeneration interrupted by user.")
            except Exception as e:
                print(f"Error during generation: {e}")




        elif choice == "0":
            print("Exiting...")
            break

        else:
            print("Invalid option. Please choose a number from 0-3.")


if __name__ == "__main__":
    main()



