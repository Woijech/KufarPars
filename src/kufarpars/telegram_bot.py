from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from html import escape
from sys import exit

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from kufarpars.bot_storage import BotStorage, UserProfile
from kufarpars.client import KufarClient, SearchRequest
from kufarpars.config import settings
from kufarpars.models import Listing

router = Router()
storage = BotStorage(settings.bot_state_path)

CALLBACK_MAIN = "menu:main"
CALLBACK_FILTERS = "menu:filters"
CALLBACK_TYPE = "filter:type"
CALLBACK_PRICE = "filter:price"
CALLBACK_RUN_ONCE = "action:run_once"
CALLBACK_WATCH_ON = "action:watch_on"
CALLBACK_WATCH_OFF = "action:watch_off"
CALLBACK_SETTINGS = "action:settings"


@dataclass(frozen=True)
class PriceRange:
    """Describes one price preset shown as an inline keyboard button."""

    code: str
    title: str
    min_price: int | None
    max_price: int | None


PRICE_RANGES = [
    PriceRange("any", "Любая цена", None, None),
    PriceRange("0_150", "до 150 $", 0, 150),
    PriceRange("150_250", "150-250 $", 150, 250),
    PriceRange("250_350", "250-350 $", 250, 350),
    PriceRange("350_500", "350-500 $", 350, 500),
    PriceRange("500_800", "500-800 $", 500, 800),
    PriceRange("800_1200", "800-1200 $", 800, 1200),
]


@router.message(Command("start", "menu"))
async def start(message: Message) -> None:
    """Open the main bot menu and create a default user profile if needed."""
    profile = ensure_default_profile(message.chat.id)
    await message.answer(
        main_menu_text(profile),
        reply_markup=main_menu_keyboard(profile),
        disable_web_page_preview=True,
    )


@router.message(Command("settings"))
async def show_settings(message: Message) -> None:
    """Show current search settings for users who prefer a direct command."""
    profile = ensure_default_profile(message.chat.id)
    await message.answer(
        settings_text(profile),
        reply_markup=main_menu_keyboard(profile),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == CALLBACK_MAIN)
async def main_menu(callback: CallbackQuery) -> None:
    """Render the main menu after a user presses the back/home button."""
    profile = ensure_default_profile(callback.message.chat.id)
    await callback.message.edit_text(
        main_menu_text(profile),
        reply_markup=main_menu_keyboard(profile),
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == CALLBACK_FILTERS)
async def filters_menu(callback: CallbackQuery) -> None:
    """Render the compact filter menu with only supported user-facing filters."""
    profile = ensure_default_profile(callback.message.chat.id)
    await callback.message.edit_text(
        filters_menu_text(profile),
        reply_markup=filters_keyboard(),
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == CALLBACK_TYPE)
async def property_type_menu(callback: CallbackQuery) -> None:
    """Render apartment/room selection buttons."""
    profile = ensure_default_profile(callback.message.chat.id)
    await callback.message.edit_text(
        "Выбери тип жилья:",
        reply_markup=property_type_keyboard(profile),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set:type:"))
async def set_property_type(callback: CallbackQuery) -> None:
    """Persist the selected property type and reset seen listings."""
    property_type = callback.data.rsplit(":", maxsplit=1)[-1]
    profile = ensure_default_profile(callback.message.chat.id)
    profile.request = replace_request(profile.request, property_type=property_type)
    profile.seen_ids = []
    storage.update(profile)
    await callback.message.edit_text(
        filters_menu_text(profile),
        reply_markup=filters_keyboard(),
        disable_web_page_preview=True,
    )
    await callback.answer("Тип жилья сохранён")


@router.callback_query(F.data == CALLBACK_PRICE)
async def price_menu(callback: CallbackQuery) -> None:
    """Render price range presets."""
    profile = ensure_default_profile(callback.message.chat.id)
    await callback.message.edit_text(
        "Выбери диапазон цены:",
        reply_markup=price_keyboard(profile),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set:price:"))
async def set_price(callback: CallbackQuery) -> None:
    """Persist the selected price range and reset seen listings."""
    code = callback.data.rsplit(":", maxsplit=1)[-1]
    price_range = price_range_by_code(code)
    profile = ensure_default_profile(callback.message.chat.id)
    profile.request = replace_request(
        profile.request,
        min_price=price_range.min_price,
        max_price=price_range.max_price,
    )
    profile.seen_ids = []
    storage.update(profile)
    await callback.message.edit_text(
        filters_menu_text(profile),
        reply_markup=filters_keyboard(),
        disable_web_page_preview=True,
    )
    await callback.answer("Цена сохранена")


@router.callback_query(F.data == CALLBACK_SETTINGS)
async def settings_callback(callback: CallbackQuery) -> None:
    """Show current settings from an inline button."""
    profile = ensure_default_profile(callback.message.chat.id)
    await callback.message.edit_text(
        settings_text(profile),
        reply_markup=main_menu_keyboard(profile),
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == CALLBACK_RUN_ONCE)
async def run_once_callback(callback: CallbackQuery) -> None:
    """Fetch current listings once and send several matching examples."""
    profile = ensure_default_profile(callback.message.chat.id)
    await callback.answer("Проверяю Kufar...")
    await callback.message.answer("Проверяю Kufar по выбранным фильтрам...")
    listings = await fetch_listings(profile)
    if not listings:
        await callback.message.answer(
            "Ничего не нашёл по текущим фильтрам.",
            reply_markup=main_menu_keyboard(profile),
        )
        return
    for listing in listings[:5]:
        await callback.message.answer(
            format_listing(listing),
            disable_web_page_preview=True,
        )
    await callback.message.answer(
        f"Показал первые {min(len(listings), 5)} из {len(listings)}.",
        reply_markup=main_menu_keyboard(profile),
    )


@router.callback_query(F.data == CALLBACK_WATCH_ON)
async def watch_on_callback(callback: CallbackQuery) -> None:
    """Enable monitoring and remember current listings as already seen."""
    profile = ensure_default_profile(callback.message.chat.id)
    await callback.answer("Включаю слежение...")
    listings = await fetch_listings(profile)
    profile.enabled = True
    profile.seen_ids = merge_seen([], listings)
    storage.update(profile)
    await callback.message.edit_text(
        "Слежение включено.\n"
        "Текущие объявления запомнил, новые пришлю отдельными сообщениями.\n\n"
        f"Запомнено объявлений: {len(profile.seen_ids)}",
        reply_markup=main_menu_keyboard(profile),
    )


@router.callback_query(F.data == CALLBACK_WATCH_OFF)
async def watch_off_callback(callback: CallbackQuery) -> None:
    """Disable monitoring for the current chat."""
    profile = ensure_default_profile(callback.message.chat.id)
    profile.enabled = False
    storage.update(profile)
    await callback.message.edit_text(
        "Слежение выключено.",
        reply_markup=main_menu_keyboard(profile),
    )
    await callback.answer()


async def notifier_loop(bot: Bot) -> None:
    """Continuously poll Kufar and notify enabled chats about new listings."""
    while True:
        for profile in storage.all_enabled():
            await notify_profile(bot, profile)
        await asyncio.sleep(settings.bot_poll_interval_seconds)


async def notify_profile(bot: Bot, profile: UserProfile) -> None:
    """Check one profile and send only listings that were not seen before."""
    try:
        listings = await fetch_listings(profile)
    except Exception:
        logging.exception("Failed to check Kufar for chat %s", profile.chat_id)
        return

    known_ids = set(profile.seen_ids)
    new_listings = [listing for listing in listings if listing.ad_id not in known_ids]
    if not new_listings:
        profile.seen_ids = merge_seen(profile.seen_ids, listings)
        storage.update(profile)
        return

    for listing in reversed(new_listings):
        await bot.send_message(
            profile.chat_id,
            format_listing(listing),
            disable_web_page_preview=True,
        )
    profile.seen_ids = merge_seen(profile.seen_ids, listings)
    storage.update(profile)


async def fetch_listings(profile: UserProfile) -> list[Listing]:
    """Fetch matching listings in a worker thread so aiogram stays responsive."""

    def fetch() -> list[Listing]:
        """Run the synchronous Kufar client for one profile."""
        with KufarClient() as client:
            return list(
                client.search_pages(
                    profile.request,
                    max_pages=settings.bot_max_pages,
                    delay_seconds=settings.bot_page_delay_seconds,
                )
            )

    return await asyncio.to_thread(fetch)


def ensure_default_profile(chat_id: int) -> UserProfile:
    """Return a profile configured for Minsk rental search by default."""
    profile = storage.get(chat_id)
    profile.request = replace_request(
        profile.request,
        city="minsk",
        deal="rent",
        currency="USD",
        sort="newest",
        text=None,
        extra_params={},
    )
    storage.update(profile)
    return profile


def replace_request(request: SearchRequest, **changes: object) -> SearchRequest:
    """Create a modified SearchRequest without mutating the original object."""
    data = {
        "city": request.city,
        "deal": request.deal,
        "property_type": request.property_type,
        "rooms": request.rooms,
        "min_price": request.min_price,
        "max_price": request.max_price,
        "currency": request.currency,
        "text": request.text,
        "sort": request.sort,
        "size": request.size,
        "extra_params": dict(request.extra_params),
    }
    data.update(changes)
    return SearchRequest(**data)


def merge_seen(seen_ids: list[int], listings: list[Listing]) -> list[int]:
    """Merge freshly fetched listing ids into the persistent seen-id list."""
    merged = [listing.ad_id for listing in listings]
    merged.extend(item for item in seen_ids if item not in merged)
    return merged[:1000]


def price_range_by_code(code: str) -> PriceRange:
    """Find a configured price range by callback code."""
    for price_range in PRICE_RANGES:
        if price_range.code == code:
            return price_range
    raise ValueError(f"Unknown price range: {code}")


def main_menu_keyboard(profile: UserProfile) -> InlineKeyboardMarkup:
    """Build the main inline keyboard for navigation and monitoring actions."""
    watch_button = (
        InlineKeyboardButton(
            text="Выключить слежение",
            callback_data=CALLBACK_WATCH_OFF,
        )
        if profile.enabled
        else InlineKeyboardButton(
            text="Включить слежение",
            callback_data=CALLBACK_WATCH_ON,
        )
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Настроить фильтры",
                    callback_data=CALLBACK_FILTERS,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Проверить сейчас",
                    callback_data=CALLBACK_RUN_ONCE,
                )
            ],
            [watch_button],
            [InlineKeyboardButton(text="Мои фильтры", callback_data=CALLBACK_SETTINGS)],
        ]
    )


def filters_keyboard() -> InlineKeyboardMarkup:
    """Build the filter selection keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Тип жилья", callback_data=CALLBACK_TYPE)],
            [InlineKeyboardButton(text="Цена", callback_data=CALLBACK_PRICE)],
            [InlineKeyboardButton(text="Назад", callback_data=CALLBACK_MAIN)],
        ]
    )


def property_type_keyboard(profile: UserProfile) -> InlineKeyboardMarkup:
    """Build buttons for choosing apartment or room search."""
    current = profile.request.property_type
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=selected_label("Квартира", current == "apartment"),
                    callback_data="set:type:apartment",
                )
            ],
            [
                InlineKeyboardButton(
                    text=selected_label("Комната", current == "room"),
                    callback_data="set:type:room",
                )
            ],
            [InlineKeyboardButton(text="Назад", callback_data=CALLBACK_FILTERS)],
        ]
    )


def price_keyboard(profile: UserProfile) -> InlineKeyboardMarkup:
    """Build buttons for choosing one predefined price range."""
    current_min = profile.request.min_price
    current_max = profile.request.max_price
    rows = []
    for price_range in PRICE_RANGES:
        is_selected = (
            price_range.min_price == current_min
            and price_range.max_price == current_max
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=selected_label(price_range.title, is_selected),
                    callback_data=f"set:price:{price_range.code}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="Назад", callback_data=CALLBACK_FILTERS)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def selected_label(text: str, selected: bool) -> str:
    """Mark the currently selected option in button text."""
    return f"[x] {text}" if selected else text


def main_menu_text(profile: UserProfile) -> str:
    """Format the main screen text with a short summary of active filters."""
    return (
        "Kufar бот для аренды жилья в Минске.\n\n"
        "Выбери фильтры кнопками, проверь выдачу и включи слежение. "
        "Когда появится новое объявление, я пришлю его сюда.\n\n"
        f"{settings_text(profile)}"
    )


def filters_menu_text(profile: UserProfile) -> str:
    """Format the filter menu text."""
    return (
        "Настрой фильтры поиска.\n\n"
        "Сейчас учитываются только тип жилья и цена.\n\n"
        f"{settings_text(profile)}"
    )


def settings_text(profile: UserProfile) -> str:
    """Format the current profile settings for display in Telegram."""
    request = profile.request
    params = "&".join(
        f"{key}={value}" for key, value in request.params().items()
    )
    return (
        f"Статус: {'включено' if profile.enabled else 'выключено'}\n"
        "Город: Минск\n"
        "Сделка: аренда\n"
        f"Тип жилья: {property_type_title(request.property_type)}\n"
        f"Цена: {price_title(request)}\n"
        f"URL: <code>{escape(request.path())}?{escape(params)}</code>"
    )


def property_type_title(property_type: str) -> str:
    """Convert internal property type code into Russian UI text."""
    return "комната" if property_type == "room" else "квартира"


def price_title(request: SearchRequest) -> str:
    """Convert the request price range into human-readable text."""
    if request.min_price is None and request.max_price is None:
        return "любая"
    min_price = request.min_price if request.min_price is not None else 0
    max_price = request.max_price if request.max_price is not None else "без лимита"
    return f"{min_price}-{max_price} {request.currency}"


def format_listing(listing: Listing) -> str:
    """Format one Kufar listing as a compact Telegram notification."""
    parts = [
        f"<b>{escape(listing.price_label)}</b> — {escape(listing.title)}",
    ]
    specs = listing_specs(listing)
    if specs:
        parts.append(escape(specs))
    if listing.short_location:
        parts.append(escape(listing.short_location))
    if listing.description:
        parts.append(escape(listing.description[:350].strip()))
    parts.append(escape(listing.url))
    return "\n".join(parts)


def listing_specs(listing: Listing) -> str:
    """Build a short room/area/floor summary for one listing."""
    parts = []
    if listing.rooms:
        parts.append(f"{listing.rooms} комн.")
    if listing.area_m2:
        parts.append(f"{listing.area_m2:g} м2")
    if listing.floor:
        floor = f"этаж {listing.floor}"
        if listing.total_floors:
            floor = f"{floor} из {listing.total_floors}"
        parts.append(floor)
    return ", ".join(parts)


@router.errors()
async def errors(event) -> None:
    """Handle user-facing validation errors and log unexpected failures."""
    update = event.update
    message = getattr(update, "message", None)
    if message is not None and isinstance(event.exception, ValueError):
        await message.answer(str(event.exception))
        return
    logging.exception("Bot error", exc_info=event.exception)


async def run_bot() -> None:
    """Create the aiogram dispatcher and run long polling."""
    if not settings.telegram_bot_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN in environment or .env file.")
    logging.basicConfig(level=logging.INFO)
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    asyncio.create_task(notifier_loop(bot))
    await dispatcher.start_polling(bot)


def main() -> None:
    """Run the bot entry point used by the console script."""
    try:
        asyncio.run(run_bot())
    except RuntimeError as error:
        print(error)
        exit(1)


if __name__ == "__main__":
    main()
