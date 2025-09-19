"""
Helper module for DinoPassAnalyzer to fetch passwords until adjective/noun saturation.
"""
import os

def fetch_until_saturation(self, target_samples=5000, batch_size=500, min_new_ratio=0.01, max_batches=20, threads=10):
    """
    Keep fetching passwords in batches until adjective/noun sets reach saturation.
    Now properly loads existing words from files and saves updates after each batch.

    Parameters:
    - target_samples: approximate total passwords to aim for.
    - batch_size: number of passwords fetched per batch.
    - min_new_ratio: minimum ratio of new words to continue fetching.
    - max_batches: maximum number of batches to fetch to avoid infinite loops.
    - threads: number of threads to fetch passwords.

    Returns: total passwords fetched.
    """
    # Load existing adjectives and nouns from files if they exist
    print("Loading existing adjectives and nouns from files...")
    initial_adj_count = len(self.adjectives)
    initial_noun_count = len(self.nouns)
    
    # Try to load existing components
    if os.path.exists("adjectives.txt") and os.path.exists("nouns.txt"):
        self.load_components("adjectives.txt", "nouns.txt")
        loaded_adj_count = len(self.adjectives)
        loaded_noun_count = len(self.nouns)
        print(f"Loaded {loaded_adj_count} existing adjectives and {loaded_noun_count} existing nouns")
    else:
        print("No existing component files found, starting fresh")
        loaded_adj_count = 0
        loaded_noun_count = 0

    total_fetched = 0
    print(f"Starting saturation fetching: aiming for ~{target_samples} passwords")
    print(f"Initial state: {len(self.adjectives)} adjectives, {len(self.nouns)} nouns")

    for batch_num in range(1, max_batches + 1):
        remaining = target_samples - total_fetched
        current_batch_size = min(batch_size, remaining)
        if current_batch_size <= 0:
            print("Target sample count reached")
            break

        print(f"\nBatch {batch_num}: Fetching {current_batch_size} passwords...")
        passwords = self.fetch_passwords_threaded(current_batch_size, max_workers=threads)
        total_fetched += len(passwords)

        # Track counts before analyzing new batch
        prev_adj_count = len(self.adjectives)
        prev_noun_count = len(self.nouns)

        # Analyze new passwords and update adjective/noun sets
        print(f"Analyzing {len(passwords)} new passwords...")
        self.analyze_corpus(passwords)

        # Compute actual growth
        new_adjs = len(self.adjectives) - prev_adj_count
        new_nouns = len(self.nouns) - prev_noun_count
        
        print(f"Batch {batch_num} results:")
        print(f"  - New adjectives discovered: {new_adjs}")
        print(f"  - New nouns discovered: {new_nouns}")
        print(f"  - Total adjectives: {len(self.adjectives)} (was {prev_adj_count})")
        print(f"  - Total nouns: {len(self.nouns)} (was {prev_noun_count})")

        # Save updated components after each batch
        print("Saving updated components to files...")
        self.save_components("adjectives.txt", "nouns.txt")

        # Calculate growth ratios for saturation check
        adj_growth_ratio = new_adjs / max(1, prev_adj_count) if prev_adj_count > 0 else 1.0
        noun_growth_ratio = new_nouns / max(1, prev_noun_count) if prev_noun_count > 0 else 1.0
        
        print(f"  - Adjective growth rate: {adj_growth_ratio:.4f} ({new_adjs}/{prev_adj_count})")
        print(f"  - Noun growth rate: {noun_growth_ratio:.4f} ({new_nouns}/{prev_noun_count})")

        # Check for saturation (both categories must be below threshold)
        if adj_growth_ratio < min_new_ratio and noun_growth_ratio < min_new_ratio and batch_num > 1:
            print(f"\nSaturation reached! Both growth rates below threshold ({min_new_ratio})")
            break
        
        # Also stop if no new words found for several batches
        if new_adjs == 0 and new_nouns == 0:
            print("No new words discovered in this batch - possible saturation")
            # Continue for one more batch to confirm
            if batch_num > 3:  # Give it a few tries before declaring saturation
                print("Confirmed saturation - no new words for multiple batches")
                break

    print(f"\nSaturation fetching complete!")
    print(f"Summary:")
    print(f"  - Total passwords fetched this session: {total_fetched}")
    print(f"  - Starting adjectives: {loaded_adj_count}")
    print(f"  - Starting nouns: {loaded_noun_count}")
    print(f"  - Final adjectives: {len(self.adjectives)} (+{len(self.adjectives) - loaded_adj_count})")
    print(f"  - Final nouns: {len(self.nouns)} (+{len(self.nouns) - loaded_noun_count})")
    print(f"  - Total new words discovered: {(len(self.adjectives) - loaded_adj_count) + (len(self.nouns) - loaded_noun_count)}")

    return total_fetched

def get_component_stats(self):
    """
    Helper function to get current component statistics
    """
    adj_file = "adjectives.txt"
    noun_file = "nouns.txt"
    
    adj_count = 0
    noun_count = 0
    
    if os.path.exists(adj_file):
        with open(adj_file, 'r') as f:
            adj_count = sum(1 for line in f if line.strip())
    
    if os.path.exists(noun_file):
        with open(noun_file, 'r') as f:
            noun_count = sum(1 for line in f if line.strip())
    
    return {
        'adjectives_in_file': adj_count,
        'nouns_in_file': noun_count,
        'adjectives_in_memory': len(self.adjectives),
        'nouns_in_memory': len(self.nouns)
    }