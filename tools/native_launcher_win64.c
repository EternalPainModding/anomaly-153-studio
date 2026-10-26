#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <stdio.h>

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR lpCmd, int nShow) {
    char exePath[MAX_PATH];
    GetModuleFileNameA(NULL, exePath, MAX_PATH);
    char *lastSlash = strrchr(exePath, '\\');
    if (lastSlash) *lastSlash = '\0';

    SetCurrentDirectoryA(exePath);
    SetEnvironmentVariableA("ANOMALY_STUDIO_ROOT", exePath);
    SetEnvironmentVariableA("ANOMALY_STUDIO_PORT", "8780");
    SetEnvironmentVariableA("PYTHONUTF8", "1");

    char cmdLine[MAX_PATH * 2];
    snprintf(cmdLine, sizeof(cmdLine), "\"%s\\python\\pythonw.exe\" \"%s\\backend\\server.py\"", exePath, exePath);

    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    ZeroMemory(&pi, sizeof(pi));

    if (!CreateProcessA(NULL, cmdLine, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, exePath, &si, &pi)) {
        snprintf(cmdLine, sizeof(cmdLine), "python \"%s\\backend\\server.py\"", exePath);
        CreateProcessA(NULL, cmdLine, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, exePath, &si, &pi);
    }

    Sleep(1200);
    ShellExecuteA(NULL, "open", "http://127.0.0.1:8780", NULL, NULL, SW_SHOWNORMAL);
    if (pi.hProcess) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
    return 0;
}
