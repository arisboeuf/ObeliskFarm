"""
Utility functions for Event Simulator.
"""


def format_number(number: float) -> str:
    """Format a number with suffixes (k, m, b, t)
    
    Examples:
        123 -> "123"
        1234 -> "1.23k"
        1234567 -> "1.23m"
    """
    if abs(number) < 1000:
        return str(int(round(number)))
    
    endings = ["", "k", "m", "b", "t"]
    oom = int(len(str(int(abs(number)))) - 1) // 3
    oom = min(oom, len(endings) - 1)
    
    return f"{number / (10 ** (oom * 3)):.2f}{endings[oom]}"


def avg_mult(chance: float, mult: float) -> float:
    """Calculate average multiplier from chance-based effect
    
    Args:
        chance: Probability (0-1) of effect triggering
        mult: Multiplier when effect triggers
    
    Returns:
        Expected average multiplier
    """
    return 1 + chance * (mult - 1)


def resources_per_minute(wave_data: tuple, resource: int, player) -> float:
    """Calculate resources per minute based on simulation results
    
    Args:
        wave_data: Tuple of (wave, subwave, time)
        resource: Which resource (1-4)
        player: Player stats
    
    Returns:
        Resources gained per minute
    """
    resource_wave_reqs = [1, 5, 10, 15]
    avg_wave = int((wave_data[0] + (((5 - wave_data[1]) / 5 - 1) if resource == 1 else 0)) / resource_wave_reqs[resource - 1])
    return (avg_wave ** 2 + avg_wave) * 120 / wave_data[2] * avg_mult(player.x5_money / 100, 5) * avg_mult(player.x2_money, 2)


def format_time(seconds: float) -> str:
    """Format seconds into a readable time string
    
    Examples:
        65.5 -> "1m 5s"
        3665 -> "1h 1m 5s"
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    secs = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {secs:.0f}s"
    
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m {secs:.0f}s"
