"""
Test script to verify cooldown persistence between runs
"""
import sys
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

from ObeliskGemEV.archaeology.monte_carlo_crit import MonteCarloCritSimulator

def test_cooldown_persistence():
    """Test that cooldowns persist correctly between runs"""
    
    # Create simulator
    simulator = MonteCarloCritSimulator(seed=42)
    
    # Test stats
    stats = {
        'total_damage': 100,
        'armor_pen': 10,
        'max_stamina': 200,
        'crit_chance': 0.15,
        'crit_damage': 1.8,
        'one_hit_chance': 0.001,
        'misc_card_level': 0,  # No misc card
    }
    
    print("=" * 60)
    print("Testing Cooldown Persistence")
    print("=" * 60)
    
    # Test 1: Enrage cooldown persistence
    print("\n1. Testing Enrage Cooldown Persistence")
    print("-" * 60)
    
    # First run - should start with cooldown = 0
    print(f"Run 1 - Initial state:")
    print(f"  persistent_enrage_state: {simulator.persistent_enrage_state}")
    
    result1 = simulator.simulate_run(
        stats, starting_floor=1,
        use_crit=True,
        enrage_enabled=True,
        flurry_enabled=False,
        quake_enabled=False,
        return_metrics=True
    )
    
    print(f"Run 1 - After simulation:")
    print(f"  persistent_enrage_state: {simulator.persistent_enrage_state}")
    print(f"  Floors cleared: {result1['floors_cleared']:.2f}")
    
    # Second run - should use cooldown from first run
    print(f"\nRun 2 - Starting state (should persist from Run 1):")
    print(f"  persistent_enrage_state: {simulator.persistent_enrage_state}")
    
    result2 = simulator.simulate_run(
        stats, starting_floor=1,
        use_crit=True,
        enrage_enabled=True,
        flurry_enabled=False,
        quake_enabled=False,
        return_metrics=True
    )
    
    print(f"Run 2 - After simulation:")
    print(f"  persistent_enrage_state: {simulator.persistent_enrage_state}")
    print(f"  Floors cleared: {result2['floors_cleared']:.2f}")
    
    # Verify persistence
    if simulator.persistent_enrage_state is not None:
        print(f"\nOK: Enrage state persisted: {simulator.persistent_enrage_state}")
        # Check that cooldown from Run 1 was used in Run 2
        if result1 and result2:
            print(f"  Run 1 ended with cooldown: {simulator.persistent_enrage_state.get('cooldown', 'N/A')}")
    else:
        print(f"\nERROR: Enrage state did NOT persist!")
    
    # Test 2: Misc Card cooldown reduction
    print("\n\n2. Testing Misc Card Cooldown Reduction")
    print("-" * 60)
    
    # Reset simulator
    simulator2 = MonteCarloCritSimulator(seed=42)
    
    # Test with Polychrome misc card (-10% cooldown)
    stats_with_card = stats.copy()
    stats_with_card['misc_card_level'] = 3  # Polychrome
    
    # Calculate expected cooldown
    expected_enrage_cooldown = int(60 * 0.90)  # 60 * 0.90 = 54
    expected_flurry_cooldown = max(10, int(120 * 0.90))  # 120 * 0.90 = 108
    expected_quake_cooldown = int(180 * 0.90)  # 180 * 0.90 = 162
    
    print(f"Base cooldowns:")
    print(f"  Enrage: 60s")
    print(f"  Flurry: 120s")
    print(f"  Quake: 180s")
    print(f"\nWith Polychrome Misc Card (-10%):")
    print(f"  Expected Enrage: {expected_enrage_cooldown}s (60 * 0.90)")
    print(f"  Expected Flurry: {expected_flurry_cooldown}s (120 * 0.90)")
    print(f"  Expected Quake: {expected_quake_cooldown}s (180 * 0.90)")
    
    # Check multiplier
    multiplier = simulator2.get_ability_cooldown_multiplier(3)
    print(f"\n  Multiplier: {multiplier} (should be 0.90)")
    
    if multiplier == 0.90:
        print(f"  OK: Multiplier correct")
    else:
        print(f"  ERROR: Multiplier incorrect! Expected 0.90, got {multiplier}")
    
    # Test 3: Flurry cooldown persistence
    print("\n\n3. Testing Flurry Cooldown Persistence")
    print("-" * 60)
    
    simulator3 = MonteCarloCritSimulator(seed=42)
    
    print(f"Run 1 - Initial state:")
    print(f"  persistent_flurry_cooldown: {simulator3.persistent_flurry_cooldown}")
    
    result3 = simulator3.simulate_run(
        stats, starting_floor=1,
        use_crit=True,
        enrage_enabled=False,
        flurry_enabled=True,
        quake_enabled=False,
        return_metrics=True
    )
    
    print(f"Run 1 - After simulation:")
    print(f"  persistent_flurry_cooldown: {simulator3.persistent_flurry_cooldown}")
    
    result4 = simulator3.simulate_run(
        stats, starting_floor=1,
        use_crit=True,
        enrage_enabled=False,
        flurry_enabled=True,
        quake_enabled=False,
        return_metrics=True
    )
    
    print(f"Run 2 - After simulation:")
    print(f"  persistent_flurry_cooldown: {simulator3.persistent_flurry_cooldown}")
    
    if simulator3.persistent_flurry_cooldown is not None:
        print(f"\nOK: Flurry cooldown persisted: {simulator3.persistent_flurry_cooldown}")
    else:
        print(f"\nERROR: Flurry cooldown did NOT persist!")
    
    # Test 4: Quake cooldown persistence
    print("\n\n4. Testing Quake Cooldown Persistence")
    print("-" * 60)
    
    simulator4 = MonteCarloCritSimulator(seed=42)
    
    print(f"Run 1 - Initial state:")
    print(f"  persistent_quake_state: {simulator4.persistent_quake_state}")
    
    result5 = simulator4.simulate_run(
        stats, starting_floor=1,
        use_crit=True,
        enrage_enabled=False,
        flurry_enabled=False,
        quake_enabled=True,
        return_metrics=True
    )
    
    print(f"Run 1 - After simulation:")
    print(f"  persistent_quake_state: {simulator4.persistent_quake_state}")
    
    result6 = simulator4.simulate_run(
        stats, starting_floor=1,
        use_crit=True,
        enrage_enabled=False,
        flurry_enabled=False,
        quake_enabled=True,
        return_metrics=True
    )
    
    print(f"Run 2 - After simulation:")
    print(f"  persistent_quake_state: {simulator4.persistent_quake_state}")
    
    if simulator4.persistent_quake_state is not None:
        print(f"\nOK: Quake state persisted: {simulator4.persistent_quake_state}")
    else:
        print(f"\nERROR: Quake state did NOT persist!")
    
    # Test 5: Verify misc card cooldown reduction is applied
    print("\n\n5. Testing Misc Card Cooldown Reduction Application")
    print("-" * 60)
    
    simulator5 = MonteCarloCritSimulator(seed=42)
    
    # Test with Polychrome card
    stats_poly = stats.copy()
    stats_poly['misc_card_level'] = 3  # Polychrome = -10%
    
    # First run with card
    result_poly = simulator5.simulate_run(
        stats_poly, starting_floor=1,
        use_crit=True,
        enrage_enabled=True,
        flurry_enabled=False,
        quake_enabled=False,
        return_metrics=True
    )
    
    print(f"With Polychrome Misc Card (-10%):")
    print(f"  persistent_enrage_state: {simulator5.persistent_enrage_state}")
    
    # Expected: 60 * 0.90 = 54
    if simulator5.persistent_enrage_state:
        cooldown_after = simulator5.persistent_enrage_state.get('cooldown', 0)
        # The cooldown should be 54 when it resets (if it resets during the run)
        # But if it doesn't reset, it could be any value < 54
        print(f"  Cooldown value: {cooldown_after}")
        print(f"  Expected effective cooldown: 54 (60 * 0.90)")
        
        # Check if multiplier was applied correctly
        multiplier_check = simulator5.get_ability_cooldown_multiplier(3)
        expected_cooldown = int(60 * multiplier_check)
        print(f"  Calculated effective cooldown: {expected_cooldown}")
        
        if cooldown_after <= expected_cooldown:
            print(f"  OK: Cooldown is within expected range (<= {expected_cooldown})")
        else:
            print(f"  WARNING: Cooldown ({cooldown_after}) exceeds expected ({expected_cooldown})")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_cooldown_persistence()
