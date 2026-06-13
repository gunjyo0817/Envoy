from unittest.mock import patch, MagicMock
import app.telegram as tg


def test_send_message_posts_to_telegram():
    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "T"}), \
         patch("app.telegram.httpx.post") as post:
        post.return_value = MagicMock(status_code=200)
        tg.tg_send(chat_id=42, text="hello", buttons=[("Accept €5", "seller:accept")])
    url, kwargs = post.call_args[0][0], post.call_args[1]
    assert url.endswith("/sendMessage")
    assert kwargs["json"]["chat_id"] == 42
    assert kwargs["json"]["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "seller:accept"


def test_build_seller_message_lists_options():
    pending = {
        "summary": "Buyer offers €170 for iPhone 14. Reply?",
        "context": {"buyer_offer": 170.0, "suggested_counter": 185.0, "draft_text": "How about 185?"},
    }
    text, buttons = tg.build_seller_message(pending)
    assert "€170" in text
    cbs = [cb for _, cb in buttons]
    assert "seller:accept" in cbs and "seller:counter" in cbs and "seller:reject" in cbs
