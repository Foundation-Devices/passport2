# Building the generator
You should only need to regenerate the ../bip39_word_info.c file if BIP39 changes,
which is extremely unlikely, or if you want to generate the same structure for words
in a different language.

To compile it:

    gcc word_list_gen.c bip39_words.c bytewords_words.c -o word_list_gen

To generate the word_info_t array:

    ./bip39_gen > ../bip39_word_info.c

You can test the output with:

    bcc bip39_test.c ../bip39_word_info.c -o bip39_test

To test:

    ./bip39_test 22       # Or any other numerical prefix
