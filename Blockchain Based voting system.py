import hashlib
import json
import time
import random
import string
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.fernet import Fernet
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import argparse
import json
import os

class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()
    
    def compute_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        
        return hashlib.sha256(block_string).hexdigest()
    
    def proof_of_work(self, difficulty):
        """Mine the block by finding a hash with specified leading zeros."""
        self.nonce = 0
        computed_hash = self.compute_hash()
        
        while not computed_hash.startswith('0' * difficulty):
            self.nonce += 1
            computed_hash = self.compute_hash()
        
        self.hash = computed_hash
        return computed_hash


class Blockchain:
    def __init__(self, difficulty=2):
        self.chain = []
        self.difficulty = difficulty
        self.pending_transactions = []
        self.genesis_created = False
    
    def create_genesis_block(self):
        """Create the first block in the chain with arbitrary previous hash."""
        if not self.genesis_created:
            genesis_block = Block(0, [], time.time(), "0")
            genesis_block.hash = genesis_block.compute_hash()
            self.chain.append(genesis_block)
            self.genesis_created = True
    
    @property
    def last_block(self):
        return self.chain[-1]
    
    def add_transaction(self, transaction):
        """Add a transaction to the pending transactions list."""
        if self.verify_transaction(transaction):
            self.pending_transactions.append(transaction)
            return True
        return False
    
    def verify_transaction(self, transaction):
        """Verify digital signature and transaction validity."""
        # Implementation depends on transaction type
        # For vote transactions, verify voter hasn't voted before
        # For registration transactions, verify identity
        return True  # Simplified for this example
    
    def mine_pending_transactions(self):
        """Create a new block with all pending transactions and add it to the chain."""
        if not self.pending_transactions:
            return False
            
        block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            timestamp=time.time(),
            previous_hash=self.last_block.hash
        )
        
        print("Mining block... This may take a moment.")
        block.proof_of_work(self.difficulty)
        self.chain.append(block)
        self.pending_transactions = []
        print(f"Block mined with hash: {block.hash[:10]}...")
        return True
    
    def is_chain_valid(self):
        """Verify the integrity of the blockchain."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Verify current block's hash
            if current.hash != current.compute_hash():
                return False
            
            # Verify current block's reference to previous block's hash
            if current.previous_hash != previous.hash:
                return False
        
        return True


@dataclass
class Voter:
    voter_id: str
    public_key: str
    district: str
    registered: bool = False
    has_voted: bool = False
    
    def generate_keys():
        """Generate a keypair for a voter."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        return private_key, public_key


class Election:
    def __init__(self, name, candidates, districts, loading = False):
        self.name = name
        self.candidates = candidates  # List of candidate names
        self.districts = districts    # List of valid districts
        self.voter_registry = {}      # voter_id -> Voter
        self.ballot_registry = {}     # district -> list of candidates
        self.blockchain = Blockchain(2)  # Lower difficulty for demo purposes
        self.election_key = self.generate_election_key()

        if not loading:
            self.blockchain.create_genesis_block()
        
    def generate_election_key(self):
        """Generate a symmetric key for tallying votes."""
        return Fernet.generate_key()
    
    def register_voter(self, voter_id, district, public_key):
        """Register a new voter."""
        if voter_id in self.voter_registry:
            return False, "Voter already registered"
        
        if district not in self.districts:
            return False, "Invalid district"
        
        # In a real system, we would verify the voter's identity here
        
        voter = Voter(voter_id=voter_id, public_key=public_key, district=district)
        self.voter_registry[voter_id] = voter
        
        # Create a registration transaction
        transaction = {
            "type": "registration",
            "voter_id": voter_id,
            "district": district,
            "public_key": public_key,
            "timestamp": time.time()
        }
        
        success = self.blockchain.add_transaction(transaction)
        if success:
            self.blockchain.mine_pending_transactions()
        
        # Mark voter as registered
            voter.registered = True
            return True, "Voter registered successfully"
    
    def prepare_ballot(self, voter_id):
        """Prepare an encrypted ballot for the voter."""
        if voter_id not in self.voter_registry:
            return None, "Voter not registered"
        
        voter = self.voter_registry[voter_id]
        if not voter.registered:
            return None, "Voter not fully registered"
        
        if voter.has_voted:
            return None, "Voter has already voted"
        
        # Get candidates for the voter's district
        district_candidates = self.ballot_registry.get(
            voter.district, 
            self.candidates  # Default to all candidates if no district-specific ballot
        )
        
        # Create ballot with a unique identifier
        ballot_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        
        ballot = {
            "ballot_id": ballot_id,
            "district": voter.district,
            "candidates": district_candidates,
            "timestamp": time.time()
        }
        
        return ballot, "Ballot prepared successfully"
    
    def cast_vote(self, voter_id, ballot_id, selected_candidate, signature):
        """Cast a vote for a candidate."""
        if voter_id not in self.voter_registry:
            return False, "Voter not registered"
        
        voter = self.voter_registry[voter_id]
        if voter.has_voted:
            return False, "Voter has already voted"
        
        # In a real system, verify the signature here
        
        # Encrypt the vote with the election key
        f = Fernet(self.election_key)
        encrypted_vote = f.encrypt(selected_candidate.encode()).decode()
        
        # Create a vote transaction
        vote_transaction = {
            "type": "vote",
            "ballot_id": ballot_id,
            "district": voter.district,
            "encrypted_vote": encrypted_vote,
            "timestamp": time.time()
        }
        
        success = self.blockchain.add_transaction(vote_transaction)
        if success:
            voter.has_voted = True
            self.blockchain.mine_pending_transactions()
            return True, "Vote cast successfully"
        
        return False, "Failed to cast vote"
    
    def tally_votes(self):
        """Count all votes and return the results."""
        vote_count = {candidate: 0 for candidate in self.candidates}
        district_results = {district: {candidate: 0 for candidate in self.candidates} 
                           for district in self.districts}
        
        f = Fernet(self.election_key)
        
        # Iterate through all blocks and count votes
        for block in self.blockchain.chain:
            for transaction in block.transactions:
                if transaction.get("type") == "vote":
                    try:
                        # Decrypt the vote
                        encrypted_vote = transaction["encrypted_vote"]
                        candidate = f.decrypt(encrypted_vote.encode()).decode()
                        district = transaction["district"]
                        
                        # Count the vote
                        if candidate in vote_count:
                            vote_count[candidate] += 1
                            district_results[district][candidate] += 1
                    except Exception as e:
                        print(f"Error counting vote: {e}")
        
        return vote_count, district_results
    
    def get_voter_participation(self):
        """Calculate voter participation statistics."""
        total_voters = len(self.voter_registry)
        voted_voters = sum(1 for voter in self.voter_registry.values() if voter.has_voted)
        
        participation_rate = (voted_voters / total_voters) * 100 if total_voters > 0 else 0
        
        district_stats = {district: {"registered": 0, "voted": 0} for district in self.districts}
        
        for voter in self.voter_registry.values():
            district_stats[voter.district]["registered"] += 1
            if voter.has_voted:
                district_stats[voter.district]["voted"] += 1
        
        return {
            "total_voters": total_voters,
            "voted_voters": voted_voters,
            "participation_rate": participation_rate,
            "district_stats": district_stats
        }
    def save_state(self, filename="election_state.json"):
        """Save the current state of the election to a file."""
        state = {
            "name": self.name,
            "candidates": self.candidates,
            "districts": self.districts,
            "voter_registry": {vid: vars(voter) for vid, voter in self.voter_registry.items()},
            "ballot_registry": self.ballot_registry,
            "blockchain": [vars(block) for block in self.blockchain.chain],
            "election_key": self.election_key.decode(),  # Convert bytes to string for JSON
            "difficulty": self.blockchain.difficulty,
            "genesis_created": self.blockchain.genesis_created
        }
        with open(filename, "w") as f:
            json.dump(state, f, indent=4)

    @staticmethod
    def load_state(filename="election_state.json"):
        """Load the election state from a file."""
        if not os.path.exists(filename):
            return None

        with open(filename, "r") as f:
            state = json.load(f)

        # Reconstruct the Election object
        election = Election(state["name"], state["candidates"], state["districts"], loading = True)
        election.ballot_registry = state["ballot_registry"]
        election.election_key = state["election_key"].encode()  # Convert string back to bytes
        election.blockchain.difficulty = state["difficulty"]

        # Reconstruct the blockchain
        for block_data in state["blockchain"]:
            block = Block(
                index=block_data["index"],
                transactions=block_data["transactions"],
                timestamp=block_data["timestamp"],
                previous_hash=block_data["previous_hash"],
                nonce=block_data["nonce"]
            )
            block.hash = block_data["hash"]  # Restore the computed hash
            election.blockchain.chain.append(block)

        election.blockchain.genesis_created = state.get("genesis_created", False)

        # Reconstruct the voter registry
        for vid, voter_data in state["voter_registry"].items():
            voter = Voter(
                voter_id=voter_data["voter_id"],
                public_key=voter_data["public_key"],
                district=voter_data["district"],
                registered=voter_data["registered"],
                has_voted=voter_data["has_voted"]
            )
            election.voter_registry[vid] = voter

        return election
    


def register_voter_interactive(election, voter_id, district):
    # In a real system, we would generate proper keys
    # For this demo, we'll use a simplified approach
    public_key = f"pub_key_{voter_id}"
    
    print("\nRegistering voter...")
    success, message = election.register_voter(voter_id, district, public_key)
    print(message)


def cast_vote_interactive(election, voter_id, selected_candidate):

    # Check if voter exists and can vote
    if voter_id not in election.voter_registry:
        print("Voter not registered!")
        return
    
    voter = election.voter_registry[voter_id]
    if voter.has_voted:
        print("You have already voted!")
        return
    
    # Get a ballot
    ballot, message = election.prepare_ballot(voter_id)
    if not ballot:
        print(message)
        return
    
    # In a real system, we would use a proper signature
    signature = "dummy_signature"
    
    print(f"\nCasting vote for {selected_candidate}...")
    success, message = election.cast_vote(
        voter_id, 
        ballot["ballot_id"], 
        selected_candidate, 
        signature
    )
    print(message)


def display_results(election):
    """Display the election results."""
    print("\n--- ELECTION RESULTS ---")
    
    results, district_results = election.tally_votes()
    
    print("\nOverall Results:")
    for candidate, votes in results.items():
        print(f"{candidate}: {votes} votes")
    
    print("\nResults by District:")
    for district, counts in district_results.items():
        print(f"\n{district}:")
        for candidate, votes in counts.items():
            print(f"  {candidate}: {votes} votes")


def display_participation(election):
    """Display voter participation statistics."""
    print("\n--- VOTER PARTICIPATION ---")
    
    stats = election.get_voter_participation()
    
    print(f"Total Registered Voters: {stats['total_voters']}")
    print(f"Total Votes Cast: {stats['voted_voters']}")
    print(f"Participation Rate: {stats['participation_rate']:.2f}%")
    
    print("\nParticipation by District:")
    for district, data in stats['district_stats'].items():
        registered = data['registered']
        voted = data['voted']
        rate = (voted / registered) * 100 if registered > 0 else 0
        print(f"{district}: {voted}/{registered} voters ({rate:.2f}%)")


def verify_blockchain(election):
    """Verify the integrity of the blockchain."""
    print("\n--- BLOCKCHAIN VERIFICATION ---")
    
    is_valid = election.blockchain.is_chain_valid()
    
    if is_valid:
        print("✅ Blockchain integrity verified!")
    else:
        print("❌ Blockchain integrity compromised!")
    
    print(f"Number of blocks: {len(election.blockchain.chain)}")
    
    # Display a summary of the blockchain
    print("\nBlockchain Summary:")
    for i, block in enumerate(election.blockchain.chain):
        transaction_count = len(block.transactions)
        print(f"Block {i}: {transaction_count} transactions, Hash: {block.hash[:10]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blockchain Voting System CLI")
    parser.add_argument('--action', required=True, choices=['register', 'vote', 'results', 'participation', 'verify'])
    parser.add_argument('--voter_id', required=False)
    parser.add_argument('--district', required=False)
    parser.add_argument('--candidate', required=False)
    
    args = parser.parse_args()

    # Load or initialize the election state
    election = Election.load_state("election_state.json")
    if not election:
        # Initialize a new election if no state exists
        candidates = ["Candidate A", "Candidate B", "Candidate C"]
        districts = ["District 1", "District 2", "District 3"]
        election = Election("General Election 2025", candidates, districts)

    try:
        if args.action == 'register':
            register_voter_interactive(election, args.voter_id, args.district)
        elif args.action == 'vote':            
            cast_vote_interactive(election, args.voter_id, args.candidate)
        elif args.action == 'results':
            display_results(election)
        elif args.action == 'participation':
            display_participation(election)
        elif args.action == 'verify':
            verify_blockchain(election)
    finally:
        # Save the election state before exiting
        election.save_state("election_state.json")