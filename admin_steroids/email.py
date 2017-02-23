from __future__ import print_function

import logging

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger(__name__)

class DevelopmentEmailBackend(EmailBackend):
    """
    Redirects all email to an specific domain address
    and appends the hostname to the message.

    Designed to be used in development environments, where
    we want to test sending real email, but don't want to risk
    emailing real users.
    """

    def _send(self, email_message):
        """
        A helper method that does the actual sending.
        """

        # Auto-bcc ourselves. This is useful when using some hosted email
        # services that don't include any "sent mail" folder by default.
        bcc_recipients = getattr(settings, 'EMAIL_BCC_RECIPIENTS', [])
        if bcc_recipients:
            email_message.bcc.extend(bcc_recipients)

        if not email_message.recipients():
            return False
        try:
            # Set recipient redirect.
            allow_any_on_domain = getattr(settings, 'DEV_EMAIL_ALLOW_ANY_ON_DOMAIN', False)
            default_redirect_to = getattr(settings, 'DEV_EMAIL_REDIRECT_TO', settings.DEV_EMAIL_REDIRECT_TO)
            default_domain = default_redirect_to.split('@')[1].strip()
            recipients = []
            if allow_any_on_domain:
                for recip in email_message.recipients():
                    # Don't redirect any of our BCC recipients.
                    if recip in bcc_recipients:
                        recipients.append(recip)
                        continue
                    try:
                        domain = recip.split('@')[1].strip()
                        if domain == default_domain:
                            recipients.append(recip)
                    except Exception as e:
                        logger.error("Invalid email recipient: %s", e)
            if not recipients:
                recipients = [default_redirect_to]
                if bcc_recipients:
                    recipients.extend(bcc_recipients)

            # Append hostname
            message = email_message.message().as_string()
            if getattr(settings, 'DEV_EMAIL_APPEND_HOSTNAME', False):
                message += '\n(Sent from %s)' % settings.BASE_URL

            self.connection.sendmail(
                from_addr=email_message.from_email,
                to_addrs=recipients,
                msg=message)
        except Exception as e:
            if not self.fail_silently:
                raise
            return False
        return True

class BCCEmailBackend(EmailBackend):

    def _send(self, email_message):

        # Auto-bcc ourselves. This is useful when using some hosted email
        # services that don't include any "sent mail" folder by default.
        bcc_recipients = getattr(settings, 'EMAIL_BCC_RECIPIENTS', [])
        if bcc_recipients:
            email_message.bcc.extend(bcc_recipients)

        super(BCCEmailBackend, self)._send(email_message)
