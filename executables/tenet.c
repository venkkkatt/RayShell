#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <dirent.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/reboot.h>

#define SNAPSHOT_DIR "/mnt/.snapshots"
#define SNAPSHOT_PATH_PREFIX "/mnt/.snapshots"
#define FLAG_FILE_PATH "/mnt/.snapshots/tenet_target.txt"
#define TEMP_FLAG_FILE_PATH "/mnt/.snapshots/tenet_target.txt.tmp"
#define MAX_SNAPNAME 128
#define MAX_CMD_LEN 512

static long target_seconds_ago = 0;

void strrev(char *str) {
    int len = strlen(str);
    for (int i = 0; i < len / 2; i++) {
        char temp = str[i];
        str[i] = str[len - i - 1];
        str[len - i - 1] = temp;
    }
}

static int isEphemeral() {
    FILE *fp;
    char buffer[128];
    int result = 0;
    
    const char *cmd = "findmnt -n -o FSTYPE / | head -n 1";

    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: popen failed to execute 'findmnt' for isEphemeral check.\n");
        return 0; 
    }

    if (fgets(buffer, sizeof(buffer), fp) != NULL) {
        buffer[strcspn(buffer, "\n")] = 0; 
        
        if (strcmp(buffer, "overlay") == 0) {
            result = 1; 
        }
    }

    pclose(fp);
    return result;
}

void generateTimestamp(char *buffer) {
    time_t timer;
    struct tm *tm_info;
    time(&timer);
    tm_info = localtime(&timer);
    strftime(buffer, 32, "%Y-%m-%d-%H%M%S", tm_info);
}

int executeCmd(const char *cmd) {
        printf("DEBUG: Executing command: %s\n", cmd);
    int status = system(cmd);
    
    if (status == -1) {
        fprintf(stderr, "DEBUG: system() failed to execute: %s\n", strerror(errno));
        return 1;
    } else if (WIFEXITED(status) && WEXITSTATUS(status) != 0) {
        fprintf(stderr, "DEBUG: Command failed with exit status %d.\n", WEXITSTATUS(status));
        return 1;
    } else if (WIFSIGNALED(status)) {
        fprintf(stderr, "DEBUG: Command terminated by signal %d.\n", WTERMSIG(status));
        return 1;
    }
    return 0;
}

static int parseTimeArg(const char *arg) {
    long value;
    char unit = 'm';
    
    if (!arg || arg[0] != '-') {
        fprintf(stderr, "ERROR: Time must be begin with '-' (eg: -2m, -5h)\n");
        return 1;
    }

    if (sscanf(arg + 1, "%ld%c", &value, &unit) != 2) {
        if (sscanf(arg + 1, "%ld", &value) != 1) {
            fprintf(stderr, "ERROR: Invalid time format. Use -Nh, -Nm, or -Nd.\n");
            return 1;
        }
        unit = 'm';
    }

    if (value <= 0) {
        fprintf(stderr, "ERROR: Time duration must be positive.\n");
        return 1;
    }

    switch (unit) {
        case 'm': case 'M': target_seconds_ago = value * 60L; break;
        case 'h': case 'H': target_seconds_ago = value * 3600L; break;
        case 'd': case 'D': target_seconds_ago = value * 86400L; break;
        default: 
            fprintf(stderr, "ERROR: Invalid time unit '%c'. Use m, h, or d", unit);
    }
    return 0;
}

static time_t parseSnapshotTime(const char *name) {
    struct tm tm;
    int year, month, day, hh, mm, ss;

    if(!name)
        return (time_t)0;
    
    if (strlen(name) != 17) 
        return (time_t)0;
    
    if (sscanf(name, "%4d-%2d-%2d-%2d%2d%2d", &year, &month, &day, &hh, &mm, &ss) != 6) {
        return (time_t)0;
    }

    memset(&tm, 0, sizeof(tm));
    tm.tm_year = year - 1900;
    tm.tm_mon = month - 1;
    tm.tm_mday = day;
    tm.tm_hour = hh;
    tm.tm_min = mm;
    tm.tm_sec = ss;
    tm.tm_isdst = -1;

    return mktime(&tm);
}

static int findBestSnapshot(char *best_snapshot_name, size_t buflen) {
    DIR *dir = NULL;
    struct dirent *entry;
    time_t now = time(NULL);
    time_t target_time = now - target_seconds_ago;
    time_t best_time = 0;
    char pathbuf[PATH_MAX];

    dir = opendir(SNAPSHOT_PATH_PREFIX);
    if (!dir) {
        fprintf(stderr, "ERROR: Cannot open snapshot directory '%s': %s", SNAPSHOT_PATH_PREFIX, strerror(errno));
        return 1;
    }

    best_snapshot_name[0] = '\0';

    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_name[0] == '.') continue;

        snprintf(pathbuf, sizeof(pathbuf), "%s/%s", SNAPSHOT_PATH_PREFIX, entry->d_name);
        struct stat st;
        if (stat(pathbuf, &st) != 0) {
            fprintf(stderr, "WARNING: Cannot stat %s: %s\n", pathbuf, strerror(errno));
            continue;
        };

        if (!S_ISDIR(st.st_mode)) continue;

        if (strlen(entry->d_name) != 17 || entry->d_name[4] != '-' || entry->d_name[7] != '-') {
            continue;
        }

        time_t snap_time = parseSnapshotTime(entry->d_name);
        if (snap_time == 0) continue;

        if (snap_time <= target_time) {
            if(snap_time > best_time) {
                best_time = snap_time;
                strncpy(best_snapshot_name, entry->d_name, buflen - 1);
                best_snapshot_name[buflen - 1] = '\0';
            }
        }
    }

    closedir(dir);
    if (best_time == 0) {
        fprintf(stderr, "ERROR: No suitable snapshot found older than %ld seconds", target_seconds_ago);
        return 1;
    }
    return 0;

}

static int writeFlagAtomic(const char *content) {
    unlink(TEMP_FLAG_FILE_PATH);
    int fd = open(TEMP_FLAG_FILE_PATH, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        fprintf(stderr, "ERROR: Cannot open temporary flag file '%s': %s\n", TEMP_FLAG_FILE_PATH, strerror(errno));
        return 1;
    }

    ssize_t w = write(fd, content, strlen(content));
    if (w < 0 || (size_t)w != strlen(content)) {
        fprintf(stderr, "ERROR: Write failed to temp flag file: %s\n", strerror(errno));
        close(fd);
        unlink(TEMP_FLAG_FILE_PATH);
        return 1;
    }

    if (fsync(fd) != 0) {
        fprintf(stderr, "WARNING: fsync failed on temp flag file: %s\n", strerror(errno));
    }

    close(fd);

    if (rename(TEMP_FLAG_FILE_PATH, FLAG_FILE_PATH) != 0) {
        fprintf(stderr, "ERROR: rename temp flag -> final failed: %s\n", strerror(errno));
        unlink(TEMP_FLAG_FILE_PATH);
        return 1;
    }

    return 0;
}

int main(int argc, char *argv[]) {

    char best_snapshot_ro[MAX_SNAPNAME];
    char best_snapshot_rw[MAX_SNAPNAME];
    char flag_content[256];
    char confirm[32];
    char rollback_mode[32]; 
    char cmd_buffer[MAX_CMD_LEN];

    if (isEphemeral()) {
        fprintf(stderr, "ERROR: 'tenet' is not available in Ephemeral mode.\n");
        return 1;
    }

    if (getuid() != 0) {
        fprintf(stderr, "ERROR: 'tenet' must be run with root privileges (e.g., 'sudo tenet').\n");
        return 1;
    }

    if (argc != 2) {
        fprintf(stderr, "Usage: tenet <time_offset>\nExample: tenet -2h (travel back 2 hours in time.)\nTenet is a command which helps you travel back in time to a specific point.\n");
        return 1;
    }

    if (parseTimeArg(argv[1]) != 0) 
        return 1;
    
    printf("What's happened is happened! The system is preparing to travel backwards...");

    printf("Travelling back %ld seconds.\n", target_seconds_ago);

    if(findBestSnapshot(best_snapshot_ro, sizeof(best_snapshot_ro)) != 0) {
        return 1;
    }

    char reverseBest[MAX_SNAPNAME];
    strncpy(reverseBest, best_snapshot_ro, sizeof(reverseBest));
    reverseBest[sizeof(reverseBest) - 1] = '\0';
    strrev(reverseBest);
    printf("1. Entering the time reversal machine. %s\n", best_snapshot_ro);
    printf("%s enihcam lasrever emit eht gniretnE .1\n", reverseBest);

    if(strlen(best_snapshot_ro) + 3 >= MAX_SNAPNAME) {
        fprintf(stderr, "ERROR: Snapshot name too long for -rw suffix.");
        return 1;
    }
    snprintf(best_snapshot_rw, sizeof(best_snapshot_rw), "%.*s-rw",(int)(sizeof(best_snapshot_rw) - 4), best_snapshot_ro);

    printf("2. Creating the writable copy %s\n", best_snapshot_rw);


    snprintf(cmd_buffer, sizeof(cmd_buffer), "btrfs subvolume snapshot %s/%.17s %s/%.21s", 
             SNAPSHOT_PATH_PREFIX, best_snapshot_ro, 
             SNAPSHOT_PATH_PREFIX, best_snapshot_rw);

    if (executeCmd(cmd_buffer) != 0) {
        fprintf(stderr, "ERROR: Failed to create writable snapshot. Aborting.\n");
        return 1;
    }

    printf("\n3. Select Time Traversal Mode:\n");
    printf("   (P)ermanent Rollback: This past state becomes the new future. You cannot come back to the present!\n");
    printf("   (O)ne-Time Visit: Visit the past, changes are discarded on next shutdown. You come back to the present after reboot.\n");
    printf("   Mode (p/o)?: ");

    if (!fgets(rollback_mode, sizeof(rollback_mode), stdin)) {
        fprintf(stderr, "No input for traversal mode. Aborting.\n");
        return 1;
    }

    rollback_mode[strcspn(rollback_mode, "\n")] = 0;

    if (rollback_mode[0] == 'O' || rollback_mode[0] == 'o') {
        snprintf(flag_content, sizeof(flag_content), "ONETIME:%s", best_snapshot_rw);
        printf("   [INFO] Traversal set to ONE-TIME VISIT.\n");
    } else {
        snprintf(flag_content, sizeof(flag_content), "%s", best_snapshot_rw);
        printf("   [INFO] Traversal set to be PERMANENT. Erasing the present!\n");
    }

    printf("4) Turning on the time reversal machine: %s\n", FLAG_FILE_PATH);
    printf("   Flag content: %s\n", flag_content);

    if (writeFlagAtomic(flag_content) != 0) {
        fprintf(stderr, "ERROR: Could not write rollback flag atomically.\n");
        return 1;
    }

    printf("\n------------------------------------------------\n");
    char reverseBrw[MAX_SNAPNAME];
    strncpy(reverseBrw, best_snapshot_rw, sizeof(reverseBrw));
    reverseBrw[sizeof(reverseBrw) - 1] = '\0';
    strrev(reverseBrw);
    printf("%s  :kcab gnisrevart won si metsyS\n", reverseBrw);
    printf("System is now traversing back: %s\n", best_snapshot_rw);

    printf("------------------------------------------------\n");
    printf("\n:(n/Y) ? etavitca ot won TOOBER\n");
    printf("REBOOT now to activate ? (Y/n): ");
    
    if (!fgets(confirm, sizeof(confirm), stdin)) {
        fprintf(stderr, "No input. Aborting.\n");
        return 1;
    }

    if (confirm[0] == 'Y' || confirm[0] == 'y' || confirm[0] == '\n') {
        printf("Rebooting system now...\n");
        sync();
        sync();
        sleep(1);
        sync();
        sleep(1);

        if (access("/usr/sbin/trinity", X_OK) == 0) {
            if (executeCmd("trinity reboot") != 0) {
                fprintf(stderr, "ERROR: trinity reboot command failed. Please reboot manually.\n");
                return 1;
            }
        } else {
            fprintf(stderr, "WARNING: /usr/sbin/trinity not found, using fallback reboot.\n");
            if (executeCmd("reboot") != 0 && executeCmd("systemctl reboot") != 0) {
                fprintf(stderr, "ERROR: reboot failed. Please reboot manually.\n");
                return 1;
            }
        }
    } else {
        printf("Rollback flag set. Reboot manually to activate.\n");
    }
    return 0;
}