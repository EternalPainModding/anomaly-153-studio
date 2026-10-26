#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/wait.h>

static pid_t child_pid = 0;

static void cleanup_handler(int sig) {
    (void)sig;
    if (child_pid > 0) {
        kill(child_pid, SIGTERM);
    }
    exit(0);
}

int main(int argc, char **argv) {
    char exe_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len < 0) {
        perror("readlink");
        return 1;
    }
    exe_path[len] = '\0';
    char *slash = strrchr(exe_path, '/');
    if (slash) *slash = '\0';

    if (chdir(exe_path) != 0) {
        perror("chdir");
        return 1;
    }

    setenv("ANOMALY_STUDIO_ROOT", exe_path, 1);

    int force_web = 0;
    const char *self_test_arg = NULL;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--web") == 0 || strcmp(argv[i], "--dev") == 0 || strcmp(argv[i], "--127") == 0) {
            force_web = 1;
        } else if (strncmp(argv[i], "--self-test-ms=", 15) == 0) {
            self_test_arg = argv[i];
        }
    }

    signal(SIGINT, cleanup_handler);
    signal(SIGTERM, cleanup_handler);

    int has_display = (getenv("DISPLAY") != NULL || getenv("WAYLAND_DISPLAY") != NULL);

    if (!force_web && has_display) {
        printf("[Anomaly Studio v0.1.1-alpha] Launching Native Desktop Application (anomaly://studio/ In-Process, 0 network ports)...\n");
        printf("[Anomaly Studio v0.1.1-alpha] Tip: Pass '--web' or '--dev' to run the 127.0.0.1:8780 Dev/Debug & macOS Web Server edition.\n");
        fflush(stdout);

        char native_script[PATH_MAX + 64];
        snprintf(native_script, sizeof(native_script), "%s/backend/native_desktop_app.py", exe_path);
        if (self_test_arg) {
            execlp("python3", "python3", native_script, self_test_arg, NULL);
        } else {
            execlp("python3", "python3", native_script, NULL);
        }
        perror("execlp native_desktop_app.py");
        return 1;
    }

    const char *port = getenv("ANOMALY_STUDIO_PORT");
    if (!port || !*port) {
        port = "8780";
        setenv("ANOMALY_STUDIO_PORT", port, 1);
    }

    printf("[Anomaly Studio v0.1.1-alpha] Starting Dev/Web Server Edition at http://127.0.0.1:%s ...\n", port);
    fflush(stdout);

    child_pid = fork();
    if (child_pid == 0) {
        char srv_script[PATH_MAX + 64];
        snprintf(srv_script, sizeof(srv_script), "%s/backend/server.py", exe_path);
        execlp("python3", "python3", srv_script, NULL);
        perror("execlp python3");
        _exit(1);
    }

    usleep(900000);
    if (has_display) {
        char url_cmd[256];
        snprintf(url_cmd, sizeof(url_cmd), "xdg-open http://127.0.0.1:%s >/dev/null 2>&1 &", port);
        int rc = system(url_cmd);
        (void)rc;
    }

    int status = 0;
    waitpid(child_pid, &status, 0);
    return 0;
}
