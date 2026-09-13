import os
import sys


def _install_direct_mode_fixes():
    try:
        import gltest.direct.loader as loader
        import gltest.direct.sdk_loader as sdk_loader
        import gltest.direct.wasi_mock as wasi_mock
        from gltest.direct.vm import VMContext
    except ImportError:
        return

    if not getattr(sdk_loader, "_autobounty_pinned", False):
        sdk_loader.get_latest_version = lambda: "v0.2.16"
        sdk_loader._autobounty_pinned = True

    if not getattr(wasi_mock, "_autobounty_template_fix", False):
        original_handle = wasi_mock._handle_gl_call

        def handle_with_templates(vm, request):
            if isinstance(request, dict) and "ExecPromptTemplate" in request:
                tpl = request["ExecPromptTemplate"]
                synthetic = "ExecPromptTemplate " + " ".join(
                    str(v) for v in tpl.values() if isinstance(v, (str, int, float, bool))
                )
                return wasi_mock._handle_llm_request(vm, {"prompt": synthetic})
            return original_handle(vm, request)

        wasi_mock._handle_gl_call = handle_with_templates
        wasi_mock._autobounty_template_fix = True

    if sys.platform == "win32" and not getattr(loader, "_autobounty_stdin_fix", False):
        original_inject = loader._inject_message_to_fd0

        def inject_with_deferred_unlink(vm):
            import tempfile

            from genlayer.py import calldata
            from genlayer.py.types import Address

            sender_addr = vm.sender
            if isinstance(sender_addr, bytes):
                sender_addr = Address(sender_addr)
            contract_addr = vm._contract_address
            if isinstance(contract_addr, bytes):
                contract_addr = Address(contract_addr)
            origin_addr = vm.origin
            if isinstance(origin_addr, bytes):
                origin_addr = Address(origin_addr)

            message_data = {
                "contract_address": contract_addr,
                "sender_address": sender_addr,
                "origin_address": origin_addr,
                "stack": [],
                "value": vm._value,
                "datetime": vm._datetime,
                "is_init": False,
                "chain_id": vm._chain_id,
                "entry_kind": 0,
                "entry_data": b"",
                "entry_stage_data": None,
            }
            encoded = calldata.encode(message_data)
            fd, path = tempfile.mkstemp()
            try:
                os.write(fd, encoded)
                os.lseek(fd, 0, os.SEEK_SET)
                original_stdin = os.dup(0)
                vm._original_stdin_fd = original_stdin
                os.dup2(fd, 0)
            finally:
                os.close(fd)
                try:
                    os.unlink(path)
                except PermissionError:
                    vm._message_temp_path = path

        loader._inject_message_to_fd0 = inject_with_deferred_unlink

        original_cleanup = VMContext._cleanup_after_deactivate

        def cleanup_with_unlink(self):
            original_cleanup(self)
            tmp = getattr(self, "_message_temp_path", None)
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                self._message_temp_path = None

        VMContext._cleanup_after_deactivate = cleanup_with_unlink
        loader._autobounty_stdin_fix = True


_install_direct_mode_fixes()
