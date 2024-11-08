// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//
#include <libgen.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <getopt.h>

#define EXTENSION "-secrets"

static char* bootloader;
static char* secrets;
static bool  debug_log_level;

static void usage(char* name) {
    printf("Usage: %s\n", name);
    printf(
        "\t-d: debug logging\n"
        "\t-b <bootloader binary>: full path to bootloader binary file\n"
        "\t-s <secrets binary>: full path to secrets binary file\n"
        "\t-h: this message\n");
    exit(1);
}

static void process_args(int argc, char** argv) {
    int c = 0;

    while ((c = getopt(argc, argv, "dhb:s:")) != -1) {
        switch (c) {
            case 'b':
                bootloader = optarg;
                break;
            case 's':
                secrets = optarg;
                break;
            case 'd':
                debug_log_level = true;
                break;
            case 'h':
            default:
                usage(argv[0]);
                break;
        }
    }
}

static int read_file(char* path, uint8_t** buffer, size_t* size) {
    size_t      ret = 0;
    struct stat info;
    FILE*       fp;

    fp = fopen(path, "r");
    if (fp == NULL) {
        printf("failed to open %s\n", path);
        return -1;
    }

    stat(path, &info);
    *buffer = (uint8_t*)calloc(1, info.st_size + sizeof(ulong));
    if (*buffer == NULL) {
        printf("insufficient memory\n");
        return -1;
    }

    ret = fread(*buffer, 1, info.st_size, fp);
    if (ret != info.st_size) {
        fclose(fp);
        free(*buffer);
        return -1;
    }

    fclose(fp);
    *size = info.st_size;
    return 0;
}

static int add_secrets(char* bl, char* secrets) {
    int      iret = 0;
    size_t   ret  = 0;
    size_t   bl_len;
    size_t   secrets_len;
    uint8_t* bl_buf      = NULL;
    uint8_t* secrets_buf = NULL;
    FILE*    fp          = NULL;
    size_t   outfile_sz  = 0;
    char*    outfile;
    char*    path;
    char*    filename;
    char*    file;
    char*    tmp;

    if (bl == NULL) {
        printf("bootloader not specified\n");
        return 1;
    }
    tmp = strdup(bl);

    filename = basename(tmp);
    if (filename == NULL) {
        free(tmp);
        printf("basename() failed\n");
        return 1;
    }

    path = dirname(tmp);
    if (path == NULL) {
        free(tmp);
        printf("dirname() failed\n");
        return 1;
    }

    file = strtok(filename, ".");
    if (file == NULL) {
        free(tmp);
        printf("strtok() failed\n");
        return 1;
    }

    outfile_sz = strlen(bl) + strlen(EXTENSION) + 1;
    outfile    = calloc(sizeof(char), outfile_sz);
    if (outfile == NULL) {
        free(tmp);
        printf("insufficient memory\n");
        return 1;
    }

    // TODO(jeandudey): replace with snprintf_s
    iret = snprintf(outfile, outfile_sz, "%s/%s%s.bin", path, file, EXTENSION);
    if (iret < 0) {
        free(outfile);
        free(tmp);
        return 1;
    }

    if (debug_log_level) printf("Reading %s...", bl);
    iret = read_file(bl, &bl_buf, &bl_len);
    if (iret < 0) {
        printf("file %s has no data\n", bl);
        free(outfile);
        free(tmp);
        return 1;
    }
    if (debug_log_level) printf("done\n");

    if (debug_log_level) printf("Reading %s...", secrets);
    iret = read_file(secrets, &secrets_buf, &secrets_len);
    if (iret < 0) {
        printf("file %s has no data\n", secrets);
        free(bl_buf);
        free(outfile);
        free(tmp);
        return 1;
    }
    if (debug_log_level) printf("done\n");

    fp = fopen(outfile, "wb");
    if (fp == NULL) {
        printf("failed to open %s\n", outfile);
        free(secrets_buf);
        free(bl_buf);
        free(outfile);
        free(tmp);
        return 1;
    }

    if (debug_log_level) printf("Writing bootloader to %s - ", outfile);
    ret = fwrite(bl_buf, 1, bl_len, fp);
    if (ret != bl_len) {
        printf("\n%s write failed - check disk space\n", outfile);
        fclose(fp);
        unlink(outfile);
        free(secrets_buf);
        free(bl_buf);
        free(outfile);
        free(tmp);
        return 1;
    }
    if (debug_log_level) printf("done\n");

    if (debug_log_level) printf("Writing secrets to %s - ", outfile);
    ret = fwrite(secrets_buf, 1, secrets_len, fp);
    if (ret != secrets_len) {
        printf("\n%s write failed - check disk space\n", outfile);
        free(secrets_buf);
        free(bl_buf);
        free(outfile);
        free(tmp);
        fclose(fp);
        return 1;
    }
    if (debug_log_level) printf("done\n");

    free(bl_buf);
    free(secrets_buf);
    free(outfile);
    free(tmp);
    fclose(fp);

    return 0;
}

int main(int argc, char* argv[]) {
    process_args(argc, argv);
    return add_secrets(bootloader, secrets);
}