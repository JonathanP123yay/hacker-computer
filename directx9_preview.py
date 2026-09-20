import ctypes
from ctypes import wintypes


D3D_SDK_VERSION = 32
D3DADAPTER_DEFAULT = 0
D3DDEVTYPE_HAL = 1
D3DSWAPEFFECT_DISCARD = 1
D3DFMT_UNKNOWN = 0
D3DCREATE_SOFTWARE_VERTEXPROCESSING = 0x20
D3DCLEAR_TARGET = 0x1
D3DPT_LINELIST = 2
D3DFVF_XYZRHW = 0x004
D3DFVF_DIFFUSE = 0x040
WM_DESTROY = 0x0002
PM_REMOVE = 0x0001


class Vertex(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
        ("rhw", ctypes.c_float),
        ("color", wintypes.DWORD),
    ]


class PresentParameters(ctypes.Structure):
    _fields_ = [
        ("back_buffer_width", wintypes.UINT),
        ("back_buffer_height", wintypes.UINT),
        ("back_buffer_format", wintypes.UINT),
        ("back_buffer_count", wintypes.UINT),
        ("multi_sample_type", wintypes.UINT),
        ("multi_sample_quality", wintypes.DWORD),
        ("swap_effect", wintypes.UINT),
        ("device_window", wintypes.HWND),
        ("windowed", wintypes.BOOL),
        ("enable_auto_depth_stencil", wintypes.BOOL),
        ("auto_depth_stencil_format", wintypes.UINT),
        ("flags", wintypes.DWORD),
        ("full_screen_refresh_rate", wintypes.UINT),
        ("presentation_interval", wintypes.UINT),
    ]


class Message(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("w_param", wintypes.WPARAM),
        ("l_param", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("point_x", ctypes.c_long),
        ("point_y", ctypes.c_long),
    ]


_WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


def _method(pointer, index, result, arguments):
    vtable = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    function = ctypes.WINFUNCTYPE(
        result,
        ctypes.c_void_p,
        *arguments
    )(vtable[index])
    return function


class DirectX9Preview:
    def __init__(self):
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.d3d9 = ctypes.WinDLL("d3d9", use_last_error=True)
        self.user32.DefWindowProcW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        self.user32.DefWindowProcW.restype = ctypes.c_ssize_t
        self.user32.RegisterClassW.argtypes = [ctypes.c_void_p]
        self.user32.RegisterClassW.restype = wintypes.ATOM
        self.user32.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            ctypes.c_void_p,
        ]
        self.user32.CreateWindowExW.restype = wintypes.HWND
        self.user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.UpdateWindow.argtypes = [wintypes.HWND]
        self.window = None
        self.d3d = None
        self.device = None
        self._window_proc = _WNDPROC(self._window_callback)
        self._create_window()
        self._create_device()

    def _window_callback(self, window, message, w_param, l_param):
        if message == WM_DESTROY:
            self.user32.PostQuitMessage(0)
            return 0
        return self.user32.DefWindowProcW(window, message, w_param, l_param)

    def _create_window(self):
        instance = self.kernel32.GetModuleHandleW(None)
        class_name = "EyeTrackerDirectX9Preview"

        class WindowClass(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("wnd_proc", ctypes.c_void_p),
                ("cls_extra", ctypes.c_int),
                ("wnd_extra", ctypes.c_int),
                ("instance", wintypes.HINSTANCE),
                ("icon", wintypes.HICON),
                ("cursor", wintypes.HCURSOR),
                ("background", wintypes.HBRUSH),
                ("menu_name", wintypes.LPCWSTR),
                ("class_name", wintypes.LPCWSTR),
            ]

        window_class = WindowClass(
            0,
            ctypes.cast(self._window_proc, ctypes.c_void_p),
            0,
            0,
            instance,
            None,
            self.user32.LoadCursorW(None,  IDC_ARROW := 32512),
            None,
            None,
            class_name,
        )
        self.user32.RegisterClassW(ctypes.byref(window_class))
        self.window = self.user32.CreateWindowExW(
            0,
            class_name,
            "DirectX 9 Eye Model",
            0x10CF0000,
            100,
            100,
            760,
            560,
            None,
            None,
            instance,
            None,
        )
        if not self.window:
            raise RuntimeError("Could not create the DirectX 9 preview window.")
        self.user32.ShowWindow(self.window, 5)
        self.user32.UpdateWindow(self.window)

    @property
    def kernel32(self):
        if not hasattr(self, "_kernel32"):
            self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self._kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            self._kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
        return self._kernel32

    def _create_device(self):
        create_d3d9 = self.d3d9.Direct3DCreate9
        create_d3d9.restype = ctypes.c_void_p
        self.d3d = ctypes.c_void_p(create_d3d9(D3D_SDK_VERSION))
        if not self.d3d:
            raise RuntimeError("Direct3D 9 is unavailable.")

        parameters = PresentParameters(
            760,
            560,
            D3DFMT_UNKNOWN,
            1,
            0,
            0,
            D3DSWAPEFFECT_DISCARD,
            self.window,
            True,
            False,
            0,
            0,
            0,
            1,
        )
        create_device = _method(
            self.d3d,
            16,
            ctypes.c_long,
            [
                wintypes.UINT,
                wintypes.UINT,
                wintypes.HWND,
                wintypes.DWORD,
                ctypes.POINTER(PresentParameters),
                ctypes.POINTER(ctypes.c_void_p),
            ],
        )
        device = ctypes.c_void_p()
        result = create_device(
            self.d3d,
            D3DADAPTER_DEFAULT,
            D3DDEVTYPE_HAL,
            self.window,
            D3DCREATE_SOFTWARE_VERTEXPROCESSING,
            ctypes.byref(parameters),
            ctypes.byref(device),
        )
        if result < 0 or not device:
            self.close()
            raise RuntimeError("Direct3D 9 could not create a device.")
        self.device = device

    def _vertex(self, x, y, color):
        return Vertex(float(x), float(y), 0.5, 1.0, color)

    def _project(self, point):
        x, y, z = point
        perspective = 260.0 / max(0.5, z + 4.0)
        return 380.0 + x * perspective, 300.0 - y * perspective

    def update(self, gaze_x, gaze_y, average_eye_position):
        if not self.device:
            return

        messages = Message()
        while self.user32.PeekMessageW(ctypes.byref(messages), None, 0, 0, PM_REMOVE):
            if messages.message == WM_DESTROY:
                self.close()
                return
            self.user32.TranslateMessage(ctypes.byref(messages))
            self.user32.DispatchMessageW(ctypes.byref(messages))

        monitor_z = 2.0
        half_width = 1.35
        half_height = 0.82
        hit = (
            (gaze_x - 0.5) * 2.0 * monitor_z,
            -(gaze_y - 0.5) * 2.0 * monitor_z,
            monitor_z,
        )
        monitor = [
            (-half_width, half_height, monitor_z),
            (half_width, half_height, monitor_z),
            (half_width, -half_height, monitor_z),
            (-half_width, -half_height, monitor_z),
        ]
        lines = []

        def add_line(first, second, color):
            first_x, first_y = self._project(first)
            second_x, second_y = self._project(second)
            lines.extend([
                self._vertex(first_x, first_y, color),
                self._vertex(second_x, second_y, color),
            ])

        for index in range(4):
            add_line(monitor[index], monitor[(index + 1) % 4], 0xFF7391AA)
        add_line((0, 0, 0), hit, 0xFF4BE66E)
        add_line((-0.22, 0, 0), hit, 0xFF46DCEC)
        add_line((0.22, 0, 0), hit, 0xFF46DCEC)

        origin = (0.0, 0.0, 0.0)
        hit_x, hit_y = self._project(hit)
        cv2_color = 0xFFFFDC00
        lines.append(self._vertex(hit_x - 12, hit_y, cv2_color))
        lines.append(self._vertex(hit_x + 12, hit_y, cv2_color))
        lines.append(self._vertex(hit_x, hit_y - 12, cv2_color))
        lines.append(self._vertex(hit_x, hit_y + 12, cv2_color))

        self._render(lines)

    def _render(self, vertices):
        clear = _method(self.device, 43, ctypes.c_long, [wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_float, wintypes.DWORD])
        begin = _method(self.device, 41, ctypes.c_long, [])
        end = _method(self.device, 42, ctypes.c_long, [])
        set_fvf = _method(self.device, 89, ctypes.c_long, [wintypes.DWORD])
        draw = _method(self.device, 83, ctypes.c_long, [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT])
        present = _method(self.device, 17, ctypes.c_long, [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p])

        vertex_array = (Vertex * len(vertices))(*vertices)
        clear(self.device, 0, None, D3DCLEAR_TARGET, 0xFF181B20, 1.0, 0)
        if begin(self.device) >= 0:
            set_fvf(self.device, D3DFVF_XYZRHW | D3DFVF_DIFFUSE)
            draw(self.device, D3DPT_LINELIST, len(vertices) // 2, ctypes.byref(vertex_array), ctypes.sizeof(Vertex))
            end(self.device)
        present(self.device, None, None, None, None)

    def close(self):
        if self.device:
            _method(self.device, 2, ctypes.c_ulong, [])(self.device)
            self.device = None
        if self.d3d:
            _method(self.d3d, 2, ctypes.c_ulong, [])(self.d3d)
            self.d3d = None
        if self.window:
            self.user32.DestroyWindow(self.window)
            self.window = None
