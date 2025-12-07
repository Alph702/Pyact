def App():
    count, set_count = use_state(0)
    def nested():
        x, set_x = use_state(1)
    return None

def Other():
    state = use_state("a")
    return None