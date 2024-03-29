from trezor import strings, ui
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import (
    confirm_action,
    confirm_blob,
    confirm_metadata,
    confirm_output,
)
from trezor.ui.popup import Popup

DUMMY_PAYMENT_ID = b"\x00\x00\x00\x00\x00\x00\x00\x00"


if False:
    from apps.monero.signing.state import State
    from trezor.messages import (
        MoneroTransactionData,
        MoneroTransactionDestinationEntry,
    )


def _format_amount(value):
    return f"{strings.format_amount(value, 12)} XMR"


async def require_confirm_watchkey(ctx):
    await confirm_action(
        ctx,
        "get_watchkey",
        "Confirm export",
        description="Do you really want to export watch-only credentials?",
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_keyimage_sync(ctx):
    await confirm_action(
        ctx,
        "key_image_sync",
        "Confirm ki sync",
        description="Do you really want to\nsync key images?",
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_live_refresh(ctx):
    await confirm_action(
        ctx,
        "live_refresh",
        "Confirm refresh",
        description="Do you really want to\nstart refresh?",
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_tx_key(ctx, export_key=False):
    if export_key:
        description = "Do you really want to export tx_key?"
    else:
        description = "Do you really want to export tx_der\nfor tx_proof?"
    await confirm_action(
        ctx,
        "export_tx_key",
        "Confirm export",
        description=description,
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_transaction(
    ctx, state: State, tsx_data: MoneroTransactionData, network_type: int
):
    """
    Ask for confirmation from user.
    """
    from apps.monero.xmr.addresses import get_change_addr_idx

    outputs = tsx_data.outputs
    change_idx = get_change_addr_idx(outputs, tsx_data.change_dts)
    has_integrated = bool(tsx_data.integrated_indices)
    has_payment = bool(tsx_data.payment_id)

    if tsx_data.unlock_time != 0:
        await _require_confirm_unlock_time(ctx, tsx_data.unlock_time)

    for idx, dst in enumerate(outputs):
        is_change = change_idx is not None and idx == change_idx
        if is_change:
            continue  # Change output does not need confirmation
        is_dummy = change_idx is None and dst.amount == 0 and len(outputs) == 2
        if is_dummy:
            continue  # Dummy output does not need confirmation
        if has_integrated and idx in tsx_data.integrated_indices:
            cur_payment = tsx_data.payment_id
        else:
            cur_payment = None
        await _require_confirm_output(ctx, dst, network_type, cur_payment)

    if has_payment and not has_integrated and tsx_data.payment_id != DUMMY_PAYMENT_ID:
        await _require_confirm_payment_id(ctx, tsx_data.payment_id)

    await _require_confirm_fee(ctx, tsx_data.fee)
    await transaction_step(state, 0)


async def _require_confirm_output(
    ctx, dst: MoneroTransactionDestinationEntry, network_type: int, payment_id: bytes
):
    """
    Single transaction destination confirmation
    """
    from apps.monero.xmr.addresses import encode_addr
    from apps.monero.xmr.networks import net_version

    version = net_version(network_type, dst.is_subaddress, payment_id is not None)
    addr = encode_addr(
        version, dst.addr.spend_public_key, dst.addr.view_public_key, payment_id
    )

    await confirm_output(
        ctx,
        address=addr.decode(),
        amount=_format_amount(dst.amount),
        font_amount=ui.BOLD,
        br_code=ButtonRequestType.SignTx,
    )


async def _require_confirm_payment_id(ctx, payment_id: bytes):
    await confirm_blob(
        ctx,
        "confirm_payment_id",
        title="Payment ID",
        data=payment_id,
        br_code=ButtonRequestType.SignTx,
    )


async def _require_confirm_fee(ctx, fee):
    await confirm_metadata(
        ctx,
        "confirm_final",
        title="Confirm fee",
        content="{}",
        param=_format_amount(fee),
        hide_continue=True,
        hold=True,
    )


async def _require_confirm_unlock_time(ctx, unlock_time):
    await confirm_metadata(
        ctx,
        "confirm_locktime",
        "Confirm unlock time",
        "Unlock time for this transaction is set to {}",
        str(unlock_time),
        br_code=ButtonRequestType.SignTx,
    )


class TransactionStep(ui.Component):
    def __init__(self, state, info):
        super().__init__()
        self.state = state
        self.info = info

    def on_render(self):
        state = self.state
        info = self.info
        ui.header("Signing transaction", ui.ICON_SEND, ui.TITLE_GREY, ui.BG, ui.BLUE)
        p = 1000 * state.progress_cur // state.progress_total
        ui.display.loader(p, False, -4, ui.WHITE, ui.BG)
        ui.display.text_center(ui.WIDTH // 2, 210, info[0], ui.NORMAL, ui.FG, ui.BG)
        if len(info) > 1:
            ui.display.text_center(ui.WIDTH // 2, 235, info[1], ui.NORMAL, ui.FG, ui.BG)


class KeyImageSyncStep(ui.Component):
    def __init__(self, current, total_num):
        super().__init__()
        self.current = current
        self.total_num = total_num

    def on_render(self):
        current = self.current
        total_num = self.total_num
        ui.header("Syncing", ui.ICON_SEND, ui.TITLE_GREY, ui.BG, ui.BLUE)
        p = (1000 * (current + 1) // total_num) if total_num > 0 else 0
        ui.display.loader(p, False, 18, ui.WHITE, ui.BG)


class LiveRefreshStep(ui.Component):
    def __init__(self, current):
        super().__init__()
        self.current = current

    def on_render(self):
        current = self.current
        ui.header("Refreshing", ui.ICON_SEND, ui.TITLE_GREY, ui.BG, ui.BLUE)
        p = (1000 * current // 8) % 1000
        ui.display.loader(p, True, 18, ui.WHITE, ui.BG)
        ui.display.text_center(
            ui.WIDTH // 2, 145, str(current), ui.NORMAL, ui.FG, ui.BG
        )


async def transaction_step(state: State, step: int, sub_step: int | None = None):
    if step == 0:
        info = ["Signing..."]
    elif step == state.STEP_INP:
        info = ["Processing inputs", f"{sub_step + 1}/{state.input_count}"]
    elif step == state.STEP_PERM:
        info = ["Sorting..."]
    elif step == state.STEP_VINI:
        info = ["Hashing inputs", f"{sub_step + 1}/{state.input_count}"]
    elif step == state.STEP_ALL_IN:
        info = ["Processing..."]
    elif step == state.STEP_OUT:
        info = ["Processing outputs", f"{sub_step + 1}/{state.output_count}"]
    elif step == state.STEP_ALL_OUT:
        info = ["Postprocessing..."]
    elif step == state.STEP_SIGN:
        info = ["Signing inputs", f"{sub_step + 1}/{state.input_count}"]
    else:
        info = ["Processing..."]

    state.progress_cur += 1
    await Popup(TransactionStep(state, info))


async def keyimage_sync_step(ctx, current, total_num):
    if current is None:
        return
    await Popup(KeyImageSyncStep(current, total_num))


async def live_refresh_step(ctx, current):
    if current is None:
        return
    await Popup(LiveRefreshStep(current))
