from inspect import currentframe


def _get_calling_dag(offset: int = 2) -> str:
    cur_frame = currentframe()
    for _ in range(offset):
        if hasattr(cur_frame, "f_back") and cur_frame.f_back and hasattr(cur_frame.f_back, "f_globals"):
            cur_frame = cur_frame.f_back
        else:
            break
    return cur_frame.f_globals["__file__"]
