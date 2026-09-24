from apps.accounts.services.accounts import AccountService

SELF = "me"


class AccountMixin:
    """Views that act on one account, named in the URL by its id or by `me`.

    `me` is not a second set of endpoints: the signed-in account is a user like
    any other, and simply has a name it can always write without knowing its id.
    """

    def account(self, user_id: str):
        if user_id == SELF:
            return self.request.user
        return AccountService.get_visible(actor=self.request.user, user_id=int(user_id))
