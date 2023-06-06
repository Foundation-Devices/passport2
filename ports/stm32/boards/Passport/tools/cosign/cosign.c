// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
#include <libgen.h>
#include <openssl/bio.h>
#include <openssl/ec.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#include "firmware-keys.h"
#include "fwheader.h"
#include "hash.h"
#include "uECC.h"

// This is the maximum length of "-key" + "-user", "00", "01", "02", or "03"
// Also, + 1 for the folder "/"
#define KEY_NAME_MAX_LENGTH 15

static char*   firmware_type = NULL;
static char*   firmware;
static char*   version;
static bool    help;
static bool    debug_log_level;
static bool    print_header;
static uint8_t header[FW_HEADER_SIZE];
static char*   key;

extern EC_KEY* PEM_read_bio_ECPrivateKey(BIO* bp, EC_KEY** key, void* cb, void* u);

static void usage(char* name) {
    printf(
        "Version 1.4\n"
        "Usage: %s\n"
        "    -d: debug logging\n"
        "    -f <firmware file>: full path to firmware file to sign\n"
        "    -h: this message\n"
        "    -k <private key file> (e.g., -k keys/01.pem)\n"
        "    -p: Print header & signature (requires -f <firmware file> too)\n"
        "    -t <mono/color>: firmware type (Required flag)\n"
        "    -v <version>: firmware version\n\n"
        "Examples:\n"
        "  First signer:\n"
        "    %s -t color -k keys/00.pem -f firmware-COLOR.bin -v 2.0.7\n\n"

        "  Second signer:\n"
        "    %s -t color -k keys/01.pem -f firmware-COLOR-key00.bin\n\n"

        "  Print firmware header:\n"
        "    %s -p -t color -f firmware-COLOR-key00.bin\n\n",
        name, name, name, name);
    exit(1);
}

static bool is_color() {
    return strcmp(firmware_type, "color") == 0;
}

static void process_args(int argc, char** argv) {
    int c = 0;

    while ((c = getopt(argc, argv, "dht:f:v:k:p")) != -1) {
        switch (c) {
            case 't':
                firmware_type = optarg;

                if (strcmp(firmware_type, "mono") && strcmp(firmware_type, "color")) {
                    printf("ERROR: Invalid firmware type '%s'. Either 'mono' or 'color' is required.\n", firmware_type);
                    exit(1);
                }

                break;
            case 'f':
                firmware = optarg;
                break;
            case 'v':
                version = optarg;
                break;
            case 'k':
                key = optarg;
                break;
            case 'd':
                debug_log_level = true;
                break;
            case 'h':
                help = true;
                break;
            case 'p':
                print_header = true;
                break;
            default:
                usage(argv[0]);
                break;
        }
    }
}

static size_t read_file(char* path, uint8_t** buffer) {
    uint32_t    ret = 0;
    struct stat info;
    FILE*       fp;

    fp = fopen(path, "r");
    if (fp == NULL) {
        printf("ERROR: Failed to open '%s'.\n", path);
        return 0;
    }

    stat(path, &info);
    *buffer = (uint8_t*)calloc(1, info.st_size + sizeof(u_long));
    if (*buffer == NULL) {
        printf("ERROR: Insufficient memory 8.\n");
        goto out;
    }

    ret = fread(*buffer, 1, info.st_size, fp);
    if (ret != info.st_size)
        free(*buffer);
    else
        ret = info.st_size;

out:
    fclose(fp);
    return ret;
}

static uint8_t* read_private_key(char* key) {
    BIO*          in;
    EC_KEY*       eckey;
    const BIGNUM* pkey;
    int           len;
    int           keylen;
    uint8_t*      private_key = NULL;

    in = BIO_new_file(key, "r");
    if (in == NULL) {
        printf("ERROR: Key '%s' does not appear to be in PEM format.\n", key);
        return NULL;
    }

    eckey = PEM_read_bio_ECPrivateKey(in, NULL, NULL, NULL);
    if (eckey == NULL) {
        printf("ERROR: Could not read key '%s'.\n", key);
        goto out;
    }

    pkey = EC_KEY_get0_private_key(eckey);
    if (pkey == NULL) {
        printf("ERROR: Internal error: could not get binary from private key '%s'.\n", key);
        goto out;
    }

    len = BN_num_bytes(pkey);
    if (len <= 0) {
        printf("ERROR: Could not get private key length: %d\n", len);
        goto out;
    }

    private_key = (uint8_t*)calloc(1, len);
    if (private_key == NULL) {
        printf("ERROR: Insufficient memory 7.\n");
        goto out;
    }

    keylen = BN_bn2bin(pkey, private_key);
    if (keylen != len) {
        printf("ERROR: Could not convert private key '%s'.\n", key);
        goto out;
    }

out:
    BIO_free(in);
    return private_key;
}

static uint8_t* read_public_key(char* key) {
    BIO*            in;
    BN_CTX*         ctx;
    EC_KEY*         eckey;
    const EC_GROUP* ecgroup;
    const EC_POINT* ecpoint;
    BIGNUM*         pkeyx;
    BIGNUM*         pkeyy;
    uint8_t*        x;
    uint8_t*        y;
    int             rc;
    int             lenx;
    int             leny;
    int             keylen;
    uint8_t*        public_key = NULL;

    in = BIO_new_file(key, "r");
    if (in == NULL) {
        printf("ERROR: Key '%s' does not appear to be in PEM format.\n", key);
        return NULL;
    }

    eckey = PEM_read_bio_ECPrivateKey(in, NULL, NULL, NULL);
    if (eckey == NULL) {
        printf("ERROR: Could not read key '%s'.\n", key);
        goto out;
    }

    ctx = BN_CTX_new();
    if (ctx == NULL) {
        printf("ERROR: Could not get BN context.\n");
        goto out;
    }
    pkeyx = BN_new();
    if (pkeyx == NULL) {
        printf("ERROR: Insufficient memory 1.\n");
        goto out;
    }
    pkeyy = BN_new();
    if (pkeyy == NULL) {
        printf("ERROR: Insufficient memory 2.\n");
        goto out;
    }
    ecgroup = EC_KEY_get0_group(eckey);
    if (ecgroup == NULL) {
        printf("ERROR: Failed to get EC GROUP.\n");
        goto out;
    }
    ecpoint = EC_KEY_get0_public_key(eckey);
    if (ecpoint == NULL) {
        printf("ERROR: Failed to get public key from private key.\n");
        goto out;
    }
    rc = EC_POINT_get_affine_coordinates(ecgroup, ecpoint, pkeyx, pkeyy, ctx);
    if (rc == 0) {
        printf("ERROR: Get affine failed.\n");
        goto out;
    }
    lenx = BN_num_bytes(pkeyx);
    if (lenx <= 0) {
        printf("ERROR: Invalid public key length: %d\n", lenx);
        goto out;
    }
    leny = BN_num_bytes(pkeyy);
    if (leny <= 0) {
        printf("ERROR: Invalid public key length: %d\n", leny);
        goto out;
    }
    x = (uint8_t*)calloc(1, lenx);
    if (x == NULL) {
        printf("ERROR: Insufficient memory 3.\n");
        goto out;
    }
    y = (uint8_t*)calloc(1, leny);
    if (y == NULL) {
        printf("ERROR: Insufficient memory 4.\n");
        goto out;
    }
    public_key = (uint8_t*)calloc(1, lenx + leny);
    if (public_key == NULL) {
        printf("ERROR: Insufficient memory 5.\n");
        goto out;
    }
    keylen = BN_bn2bin(pkeyx, x);
    if (keylen != lenx) {
        printf("ERROR: Could not convert public key X: '%s'.\n", key);
        goto out;
    }
    keylen = BN_bn2bin(pkeyy, y);
    if (keylen != leny) {
        printf("ERROR: Could not convert public key Y: '%s'.\n", key);
        goto out;
    }

    memcpy(public_key, x, lenx);
    memcpy(&public_key[lenx], y, leny);
    BN_CTX_free(ctx);
    BN_free(pkeyx);
    BN_free(pkeyy);

out:
    BIO_free(in);
    return public_key;
}

char* remove_ext(char* str) {
    char*   ret_str;
    char*   last_ext;
    uint8_t len;

    if (str == NULL) return NULL;

    // How much to copy?
    last_ext = strrchr(str, '.');
    if (last_ext == NULL) {
        len = strlen(str);
    } else {
        len = last_ext - str;
    }

    ret_str = malloc(len + 1);
    if (ret_str == NULL) {
        return NULL;
    }

    strncpy(ret_str, str, len);
    ret_str[len] = '\0';
    return ret_str;
}

char* remove_unsigned(char* str) {
    int   len;
    char* ret_str;
    char* needle = strstr(str, "-unsigned");

    if (needle == NULL) {
        len = strlen(str);
    } else {
        len = needle - str;
    }

    ret_str = malloc(len + 1);
    if (ret_str == NULL) {
        return NULL;
    }
    strncpy(ret_str, str, len);
    ret_str[len] = '\0';
    return ret_str;
}

bool is_valid_version(char* version) {
    int  num_matched;
    int  version_major;
    int  version_minor;
    int  version_rev;
    char left_over;

    num_matched = sscanf(version, "%u.%u.%u%c", &version_major, &version_minor, &version_rev, &left_over);

    if (num_matched != 3) {
        return false;
    }

    // Version major is restricted to only 0-9 while others are 0-99
    // Max version number string is 7 + null terminator
    if (version_major > 9 || version_major < 0 || version_minor > 99 || version_minor < 0 || version_rev > 99 ||
        version_rev < 0) {
        return false;
    } else {
        sprintf(version, "%d.%d.%d", version_major, version_minor, version_rev);
        return true;
    }
}

int find_public_key(uint8_t* key) {
    int keynum;

    for (keynum = 0; keynum < FW_MAX_PUB_KEYS; ++keynum) {
        if (memcmp(approved_pubkeys[keynum], key, sizeof(approved_pubkeys[keynum])) == 0) return keynum;
    }
    return -1;
}

int magic_for_firmware_type(void) {
    if (is_color()) {
        return FW_HEADER_MAGIC_COLOR;
    } else {
        return FW_HEADER_MAGIC;
    }
}

bool is_valid_magic(uint32_t magic) {
    return magic == magic_for_firmware_type();
}

static void sign_firmware(char* fw, char* key, char* version) {
    size_t                      ret = 0;
    size_t                      fwlen;
    uint8_t*                    fwbuf  = NULL;
    FILE*                       fp     = NULL;
    char*                       output = NULL;
    char*                       path;
    char*                       tmp;
    passport_firmware_header_t* hdrptr;
    uint8_t*                    fwptr;
    uint8_t                     fw_hash[HASH_LEN];
    uint8_t*                    working_signature;
    int                         rc;
    uint8_t                     working_key = 0;
    uint8_t*                    private_key;
    uint8_t*                    public_key;

    if (fw == NULL) {
        printf("ERROR: Firmware file must be specified with: -f <firmware file>\n");
        exit(1);
        return;
    }
    if (key == NULL) {
        printf("ERROR: Private key must be specified with: -k <private key file>\n");
        exit(1);
        return;
    }

    private_key = read_private_key(key);
    if (private_key == NULL) {
        printf("ERROR: Could not read private key.\n");
        exit(1);
        return;
    }

    public_key = read_public_key(key);
    if (public_key == NULL) {
        printf("ERROR: Could not read public key.\n");
        exit(1);
        return;
    }

    rc = find_public_key(public_key);
    if (rc < 0) {
        printf("INFO: Key %s not a supported public key.  Assuming user key.\n", key);
        working_key = FW_USER_KEY;
    } else
        working_key = rc;

    tmp = strdup(fw);

    path = dirname(tmp);
    if (path == NULL) {
        printf("ERROR: dirname() failed\n");
        exit(1);
        return;
    }

    output = (char*)calloc(1, 256);
    if (output == NULL) {
        printf("ERROR: Insufficient memory (output)\n");
        exit(1);
        return;
    }

    if (debug_log_level) printf("Reading %s...", fw);
    fwlen = read_file(fw, &fwbuf);
    if (fwlen == 0) {
        printf("ERROR: File %s has no data\n", fw);
        exit(1);
        return;
    }
    if (debug_log_level) printf("Done\n");

    /*
     * Test for an existing header in the firwmare. If one exists that
     * means that it has been signed at least once already.
     */
    hdrptr = (passport_firmware_header_t*)fwbuf;
    if (hdrptr->info.magic == magic_for_firmware_type()) {
        /* Looks like there is an existing header...let's validate it */
        if (hdrptr->info.timestamp == 0) {
            printf("ERROR: Existing header found, but timestamp is invalid.\n");
            exit(1);
            goto out;
        } else if (strlen((char*)hdrptr->info.fwversion) == 0) {
            printf("ERROR: Existing header found, but firmware version is invalid.\n");
            exit(1);
            goto out;
        } else if (hdrptr->info.fwlength != fwlen - FW_HEADER_SIZE) {
            printf("ERROR: Existing header found, but FW length invalid.\n");
            exit(1);
            goto out;
        } else if (hdrptr->signature.pubkey1 == FW_USER_KEY) {
            printf("ERROR: This firmware was already signed by a user private key.\n");
            exit(1);
            goto out;
        } else if (hdrptr->signature.pubkey1 == working_key) {
            printf("ERROR: This firmware was already signed by key%02d (same key cannot sign twice).\n", working_key);
            exit(1);
            goto out;
        } else if (working_key == FW_USER_KEY) {
            printf(
                "ERROR: Cannot sign firmware with a user private key after signing with a Foundation private key.\n");
            exit(1);
            goto out;
        }

        hdrptr->signature.pubkey2 = working_key;
        working_signature         = hdrptr->signature.signature2;
        fwptr                     = fwbuf + FW_HEADER_SIZE;

        // Generate output filename as the final name that goes to users
        if (is_color()) {
            sprintf(output, "%s/v%s-passport.bin", path, hdrptr->info.fwversion);
        } else {
            sprintf(output, "%s/v%s-founders-passport.bin", path, hdrptr->info.fwversion);
        }
    } else if (is_valid_magic(hdrptr->info.magic)) {
        printf("ERROR: Incompatible firmware type (Wrong magic number).\n");
        exit(1);
        goto out;
    } else {
        /* No existing header...confirm that the user specified a version */
        if (version == NULL) {
            printf("ERROR: Version number not specified.\n");
            exit(1);
            goto out;
        }

        if (!is_valid_version(version)) {
            printf("ERROR: Incorrect version number. Correct format: <0-9>.<0-99>.<0-99> (e.g., 1.12.34)\n");
            exit(1);
            goto out;
        }

        // Generate output filename
        if (working_key == FW_USER_KEY) {
            if (is_color()) {
                sprintf(output, "%s/v%s-beta-passport.bin", path, version);
            } else {
                sprintf(output, "%s/v%s-beta-founders-passport.bin", path, version);
            }
        } else {
            if (is_color()) {
                sprintf(output, "%s/v%s-passport-key%02d.bin", path, version, working_key);
            } else {
                sprintf(output, "%s/v%s-founders-passport-key%02d.bin", path, version, working_key);
            }
        }

        hdrptr = (passport_firmware_header_t*)header;

        /* Create a new header...this is the first signature. */
        time_t now             = time(NULL);
        hdrptr->info.magic     = magic_for_firmware_type();
        hdrptr->info.timestamp = now;
        struct tm now_tm       = *localtime(&now);

        // Make a string version of the date too for easier display in the bootloader
        // where we don't have fancy date/time functions.
        strftime((char*)hdrptr->info.fwdate, sizeof(hdrptr->info.fwdate), "%b %d, %Y", &now_tm);

        strcpy((char*)hdrptr->info.fwversion, version);
        hdrptr->info.fwlength     = fwlen;
        hdrptr->signature.pubkey1 = working_key;
        working_signature         = hdrptr->signature.signature1;
        fwptr                     = fwbuf;
    }

    fp = fopen(output, "wb");
    if (fp == NULL) {
        printf("ERROR: Failed to open %s\n", output);
        exit(1);
        goto out;
    }

    if (debug_log_level) {
        printf("FW header content:\n");
        printf("\ttimestamp: %d\n", hdrptr->info.timestamp);
        printf("\t   fwdate: %s\n", hdrptr->info.fwdate);
        printf("\tfwversion: %s\n", hdrptr->info.fwversion);
        printf("\t fwlength: %d\n", hdrptr->info.fwlength);
    }

    hash_fw(&hdrptr->info, fwptr, hdrptr->info.fwlength, fw_hash, HASH_LEN);

    if (debug_log_level) {
        printf("FW hash: ");
        for (int i = 0; i < HASH_LEN; ++i)
            printf("%02x", fw_hash[i]);
        printf("\n");
    }

    /* Encrypt the hash here... */
    rc = uECC_sign(private_key, fw_hash, sizeof(fw_hash), working_signature, uECC_secp256k1());
    if (rc == 0) {
        printf("signature failed\n");
        goto out;
    }

    if (working_key != FW_USER_KEY) {
        rc = uECC_verify(approved_pubkeys[working_key], fw_hash, sizeof(fw_hash), working_signature, uECC_secp256k1());
        if (rc == 0) {
            printf("ERROR: Verify signature failed.\n");
            exit(1);
            goto out;
        }
    }

    if (debug_log_level) {
        printf("signature: ");
        for (int i = 0; i < SIGNATURE_LEN; ++i)
            printf("%02x", working_signature[i]);
        printf("\n");
    }

    if (debug_log_level) printf("Writing header to %s - ", output);
    ret = fwrite(hdrptr, 1, FW_HEADER_SIZE, fp);
    if (ret != FW_HEADER_SIZE) {
        unlink(output);
        printf("\nERROR: %s write failed - check disk space\n", output);
        exit(1);
        goto out;
    }
    if (debug_log_level) printf("done\n");

    if (debug_log_level) printf("Writing firmware to %s - ", output);
    ret = fwrite(fwptr, 1, hdrptr->info.fwlength, fp);
    if (ret != hdrptr->info.fwlength) {
        unlink(output);
        printf("\nERROR: %s write failed - check disk space\n", output);
        exit(1);
        goto out;
    }
    if (debug_log_level) printf("done\n");

    printf("Wrote signed firmware to: %s\n", output);
out:
    free(fwbuf);
    free(output);
    free(tmp);
    if (fp != NULL) fclose(fp);
}

static void dump_firmware_header(char* fw) {
    size_t                      fwlen;
    uint8_t*                    fwbuf = NULL;
    passport_firmware_header_t* hdrptr;
    uint8_t                     fw_hash[HASH_LEN];

    if (fw == NULL) {
        printf("firmware not specified\n");
        return;
    }

    if (debug_log_level) printf("Reading %s...", fw);
    fwlen = read_file(fw, &fwbuf);
    if (fwlen == 0) {
        printf("ERROR: File '%s' has no data.\n", fw);
        return;
    }
    if (debug_log_level) printf("done\n");

    hdrptr = (passport_firmware_header_t*)fwbuf;
    if (hdrptr->info.magic == magic_for_firmware_type()) {
        printf("FW header content:\n");
        printf("\ttimestamp: %d\n", hdrptr->info.timestamp);
        printf("\t   fwdate: %s\n", hdrptr->info.fwdate);
        printf("\tfwversion: %s\n", hdrptr->info.fwversion);
        printf("\t fwlength: %d\n", hdrptr->info.fwlength);
        printf("\t      key: %d\n", hdrptr->signature.pubkey1);
        printf("\tsignature: ");
        for (int i = 0; i < SIGNATURE_LEN; ++i)
            printf("%02x", hdrptr->signature.signature1[i]);
        printf("\n");
        printf("\t      key: %d\n", hdrptr->signature.pubkey2);
        printf("\tsignature: ");
        for (int i = 0; i < SIGNATURE_LEN; ++i)
            printf("%02x", hdrptr->signature.signature2[i]);
        printf("\n");

        // Print hashes
        hash_fw_user(fwbuf, fwlen, fw_hash, HASH_LEN, true);

        printf("\nFW Build Hash:    ");
        for (int i = 0; i < HASH_LEN; ++i)
            printf("%02x", fw_hash[i]);
        printf("\n");

        hash_fw_user(fwbuf, fwlen, fw_hash, HASH_LEN, false);

        printf("FW Download Hash: ");
        for (int i = 0; i < HASH_LEN; ++i)
            printf("%02x", fw_hash[i]);
        printf("\n");

    } else
        printf("ERROR: No firmware header found in file '%s'.\n", fw);
}

int main(int argc, char* argv[]) {
    process_args(argc, argv);

    if (help) usage(argv[0]);

    if (firmware_type == NULL) {
        printf("ERROR: Firmware type MUST be specified with -t <mono/color>\n");
        exit(1);
    }

    if (print_header)
        dump_firmware_header(firmware);
    else
        sign_firmware(firmware, key, version);

    exit(0);
}
