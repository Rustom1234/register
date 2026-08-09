# Connecting a real WhatsApp number

The webhook receiver, signature verification, and outbound sender are
already built (`pukaar/pukaar/whatsapp.py`, `/webhook` route). This is
configuration, not coding. Budget ~30 minutes plus Meta's verification
wait.

## What you need

- A deployed Wayside URL (see [DEPLOY.md](./DEPLOY.md)) — Meta must be
  able to reach `https://<your-app>/webhook`.
- A phone number that can receive one SMS (a fresh ~₹200 SIM is fine —
  the number gets bound to WhatsApp Business and can't also run personal
  WhatsApp).
- A Facebook account for the Meta developer console.

## Steps

1. **Create the Meta app.** [developers.facebook.com](https://developers.facebook.com)
   → My Apps → Create App → type **Business**. Add the **WhatsApp**
   product to it.

2. **Get the test credentials.** WhatsApp → **API Setup** shows a free
   Meta-provided test number, a temporary access token, and the
   **Phone number ID**. You can wire everything with these first and
   swap in your real number later.

3. **Set the environment variables** on your host (Render dashboard →
   Environment):

   | Variable | Where it comes from |
   |---|---|
   | `WA_TOKEN` | API Setup → access token (later: a permanent System User token — see step 7) |
   | `WA_PHONE_ID` | API Setup → Phone number ID |
   | `WA_APP_SECRET` | App settings → Basic → App secret (signs every webhook; the app refuses to go live without it) |
   | `WA_VERIFY_TOKEN` | Any string you invent (default `pukaar-verify`) — you'll type the same string into Meta in step 4 |

   Redeploy so the variables take effect.

4. **Point the webhook at your server.** WhatsApp → **Configuration** →
   Webhook → Edit:
   - Callback URL: `https://<your-app>.onrender.com/webhook`
   - Verify token: exactly your `WA_VERIFY_TOKEN` value
   Meta sends a verification GET; the built-in handler answers it.
   Then click **Manage** and subscribe to the **messages** field.

5. **Test from your own phone.** API Setup → "To" → add your number as a
   recipient (dev mode allows up to 5), send the hello template to
   yourself once, then reply anything — your message should appear in the
   Wayside control room as a witness report, and the bot's answer should
   land back in WhatsApp.

6. **Business verification (start early).** Real traffic from arbitrary
   numbers needs Meta Business verification: Business Settings →
   Security Centre → Start verification (business name, address, a
   document). Takes days to ~2 weeks. Until then you're limited to the 5
   test recipients — enough for a staged investor demo.

7. **Go permanent.** After verification: add your real number (WhatsApp →
   API Setup → Add phone number, verified by SMS), and replace the
   temporary token with a permanent one: Business Settings → Users →
   System Users → create one, assign the app, generate a token with
   `whatsapp_business_messaging` permission. Put it in `WA_TOKEN`.

8. **Tell the world.** Posters and pitch decks use the click-to-chat
   link `https://wa.me/<countrycode><number>` — witnesses tap it and the
   chat opens with your number, nothing to save. Any QR generator turns
   that link into a poster QR.

## Costs

Witness-initiated service conversations are free at pilot scale on the
Cloud API — Meta's fees apply to business-initiated template messages,
which Wayside doesn't send (all replies happen inside the 24-hour
service window the witness opens). Budget ₹0 for messaging until you're
doing outbound campaigns.

## If you're stuck before verification clears

Use the built-in Telegram line instead (₹0, live in 5 minutes, no
verification — see DEPLOY.md). Same intake, same board, same rider flow;
only the chat app differs.
