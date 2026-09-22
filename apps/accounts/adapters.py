from allauth.account.adapter import DefaultAccountAdapter


class OrganisationAccountAdapter(DefaultAccountAdapter):
    """Use an organisation's SMTP server for unambiguous password resets."""

    def send_mail(self, template_prefix, email, context):
        if "password_reset" not in template_prefix:
            return super().send_mail(template_prefix, email, context)
        from apps.accounts.models import UserProfile
        from apps.organisations.email import fuelle_emailvorlage, sende_org_email
        from apps.organisations.models import OrganisationEmailKonfiguration

        profile = UserProfile.objects.filter(
            nutzer__email__iexact=email, aktiv=True
        ).select_related("organisation")
        if profile.count() != 1:
            return super().send_mail(template_prefix, email, context)
        org = profile.first().organisation
        config, _ = OrganisationEmailKonfiguration.objects.get_or_create(organisation=org)
        link = context.get("password_reset_url", "")
        sende_org_email(
            org,
            fuelle_emailvorlage(config.passwort_reset_betreff, organisation=org.name),
            fuelle_emailvorlage(config.passwort_reset_text, organisation=org.name, passwort_reset_link=link),
            email,
        )
