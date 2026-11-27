// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

use foundation::ur::{
    decoder::{
        UR_Decoder, UR_DECODER_MAX_FRAGMENT_LEN, UR_DECODER_MAX_MESSAGE_LEN,
        UR_DECODER_MAX_MIXED_PARTS, UR_DECODER_MAX_SEQUENCE_COUNT,
        UR_DECODER_MAX_SINGLE_PART_MESSAGE_LEN, UR_DECODER_MAX_STRING,
        UR_DECODER_QUEUE_SIZE,
    },
    encoder::{
        UR_Encoder, UR_ENCODER_MAX_FRAGMENT_LEN, UR_ENCODER_MAX_MESSAGE_LEN,
        UR_ENCODER_MAX_SEQUENCE_COUNT, UR_ENCODER_MAX_STRING,
    },
};
use std::mem::size_of;

fn main() {
    println!("{: <34} | {: <8} | {: <8}", "", "Decoder", "Encoder");
    println!(
        "{: <34} | {: <8} | {: <8}",
        "Max. Sequence Count",
        UR_DECODER_MAX_SEQUENCE_COUNT,
        UR_ENCODER_MAX_SEQUENCE_COUNT
    );
    println!(
        "{: <34} | {: <8} | {: <8}",
        "Max. UR String Length", UR_DECODER_MAX_STRING, UR_ENCODER_MAX_STRING
    );
    println!(
        "{: <34} | {: <8} | {: <8}",
        "Max. Fragment Length",
        UR_DECODER_MAX_FRAGMENT_LEN,
        UR_ENCODER_MAX_FRAGMENT_LEN
    );
    println!(
        "{: <34} | {: <8} | {: <8}",
        "Max. Message Length",
        UR_DECODER_MAX_MESSAGE_LEN,
        UR_ENCODER_MAX_MESSAGE_LEN
    );
    println!(
        "{: <34} | {: <8} | {: <8}",
        "Max. Message Length (Single-Part)",
        UR_DECODER_MAX_SINGLE_PART_MESSAGE_LEN,
        "TODO"
    );
    println!(
        "{: <34} | {: <8} | {: <8}",
        "Max. Mixed Parts", UR_DECODER_MAX_MIXED_PARTS, "Not Applicable"
    );
    println!(
        "{: <34} | {: <8} | {: <8}",
        "Queue Size", UR_DECODER_QUEUE_SIZE, "Not Applicable"
    );
    println!(
        "{: <34} | {: <8} | {: <8}",
        "Structure Size",
        size_of::<UR_Decoder>(),
        size_of::<UR_Encoder>()
    );
}
