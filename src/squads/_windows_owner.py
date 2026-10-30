"""Windows only: whether a directory belongs to the current user. The calls are the Win32 ones
through ``ctypes``, which have no type information."""
# pyright: basic

from pathlib import Path


def owner_problem(directory: Path) -> str | None:
    """Why *directory* is not owned by the current user, or ``None`` when it is or when the owner
    cannot be read (the check then gives no answer rather than refusing every start)."""
    try:
        import ctypes
        from ctypes import wintypes

        advapi = ctypes.WinDLL("advapi32", use_last_error=True)  # pyright: ignore[reportAttributeAccessIssue]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # pyright: ignore[reportAttributeAccessIssue]
        owner, descriptor = ctypes.c_void_p(), ctypes.c_void_p()
        file_object, owner_information, token_user = 1, 1, 1
        if advapi.GetNamedSecurityInfoW(
            str(directory),
            file_object,
            owner_information,
            ctypes.byref(owner),
            None,
            None,
            None,
            ctypes.byref(descriptor),
        ):
            return None
        token = wintypes.HANDLE()
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
            return None
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, token_user, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token, token_user, buffer, size, ctypes.byref(size)):
            return None
        user = ctypes.c_void_p.from_buffer(buffer).value
        if not advapi.EqualSid(ctypes.c_void_p(user), owner):
            return f"{directory} is not owned by the current user"
    except Exception:
        return None
    return None
