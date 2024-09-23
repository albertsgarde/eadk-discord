import logging

from discord import Interaction


def desk_index(index: int) -> str:
    return f"{index + 1}"


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
