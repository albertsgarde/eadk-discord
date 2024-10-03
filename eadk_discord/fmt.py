import logging
from datetime import date as Date  # noqa: N812

from beartype import beartype
from discord import Interaction


@beartype
def desk_index(index: int) -> str:
    return f"{index + 1}"


@beartype
def date(date: Date) -> str:
    return date.isoformat()


@beartype
def user(interaction: Interaction, user: int) -> str:
    match interaction.guild:
        case None:
            logging.debug("Interaction has no guild")
            return f"{user}"
        case guild:
            match guild.get_member(user):
                case None:
                    logging.debug(f"User {user} is not a member of the guild")
                    return f"{user}"
                case member:
                    return member.display_name
