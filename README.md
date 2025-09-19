# dinocrack
A comprehensive password list generator that demonstrates the predictable nature of DinoPass "strong" passwords and their vulnerability in security contexts.

## What is dinocrack
dinocrack reverse-engineers the DinoPass pattern (which is essentially [adjective][noun][2 digits], with a single leetspeak substitution) and generates targeted, high-coverage wordlist that match those patterns.

### The Vulnerability in Numbers
The tool demonstrates this vulnerability by generating a list of all **18,259,200** plausible DinoPass passwords, a finite and predictable set that is highly susceptible to focused attacks.

## Why DinoPass is a Security Concern

DinoPass poses a security risk because its passwords, while memorable, follow a limited set of predictable rules. This predictability allows attackers to build small, highly targeted dictionaries that can crack them far more quickly than truly random passwords.

Although DinoPass is marketed as a children’s tool, its passwords are often adopted by help-desk staff, system administrators, and service-desk teams for quick password generation. These professionals may assume that complexity alone provides adequate security. In reality, this is a dangerous misconception; the underlying generation method is predictable rather than random, making these passwords weak against focused attacks.

## How it works 

### 1. Pattern Analysis 

The last 2 characters (digits) are treated as a suffix and ignored during analysis.

Remaining text is split into two tokens (adjective + noun) using camelCase boundaries where possible, otherwise fallback splits are used.

Reverse-leetspeak rules attempt to map symbols back to letters (e.g. ! → i, 3 → e, < → c/k) and a spellchecker is used to pick plausible base words when a symbol could map to multiple letters.

### 2. Component extraction  

Adjectives are taken from the first token after deleeting and cleaning.

Nouns are taken from the second token (normalized to capitalized form when generating).

Single-substitution leet variants are generated from each component (exactly one leet change per word), then combined with other components and a two-digit suffix to build candidate passwords.

### 3. Password Generation

The given passwords found in ```dinopass_strong_pass.txt``` will now hold all strong passwords provided by the dinopass API (https://www.dinopass.com/password/strong)

## Features
- Multithreaded Fetch: Efficiently retrieves a corpus of strong passwords directly from the DinoPass API.

- Analyze corpus to extract adjective and noun components.

- Generate comprehensive and targeted wordlists:

- Enforces the rule: exactly one leet substitution per password component (and the final 2 digits are not counted as leet).

- Preview output to verify results before generating full lists.

## Dependencies 
```pip install requests pyspellchecker``` 

## Quick Usage
Run the main program: 
```python dinopass_generator.py```

## Security & Ethics
dinocrack is a research and educational tool to demonstrate weaknesses in predictable password generators. Use it responsibly:

Do not use these wordlists to attack systems you do not own or are not authorized to test.

Use this tool for defensive purposes: to test password policy strength, to evaluate temporary-password practices, or for academic research.

Respect local laws and institutional policies on penetration testing and password cracking.