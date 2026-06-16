<<<<<<< SEARCH
        if user_alter_statements:
            with engine.begin() as connection:
                for statement in user_alter_statements:
                    connection.execute(text(statement))
                connection.execute(
                    text("UPDATE users SET collection_visibility = 'private' WHERE collection_visibility IS NULL OR collection_visibility = ''")
                )
                connection.execute(
                    text(f'UPDATE users SET homepage_showcase_opt_in = {default_false} WHERE homepage_showcase_opt_in IS NULL')
                )
                # Asegurar índices para filtros y ordenamientos comunes
                connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_collection_visibility ON users (collection_visibility)'))
                connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_homepage_showcase_opt_in ON users (homepage_showcase_opt_in)'))
                connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at)'))
=======
        if user_alter_statements:
            with engine.begin() as connection:
                for statement in user_alter_statements:
                    connection.execute(text(statement))
                connection.execute(
                    text("UPDATE users SET collection_visibility = 'private' WHERE collection_visibility IS NULL OR collection_visibility = ''")
                )
                connection.execute(
                    text(f'UPDATE users SET homepage_showcase_opt_in = {default_false} WHERE homepage_showcase_opt_in IS NULL')
                )

        # Asegurar índices para filtros y ordenamientos comunes (Fuera del bloque condicional para mayor robustez)
        with engine.begin() as connection:
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_collection_visibility ON users (collection_visibility)'))
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_homepage_showcase_opt_in ON users (homepage_showcase_opt_in)'))
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at)'))
>>>>>>> REPLACE
<<<<<<< SEARCH
    if not alter_statements:
        return

    with engine.begin() as connection:
        for statement in alter_statements:
            connection.execute(text(statement))
        connection.execute(text("UPDATE games SET categoria = 'Biblioteca' WHERE categoria IS NULL OR categoria = ''"))
        connection.execute(text("UPDATE games SET prioridad = 'Media' WHERE prioridad IS NULL OR prioridad = ''"))
        connection.execute(text(f'UPDATE games SET es_favorito = {default_false} WHERE es_favorito IS NULL'))
        # Asegurar índices para filtros y ordenamientos comunes
        connection.execute(text('CREATE INDEX IF NOT EXISTS ix_games_created_at ON games (created_at)'))
        connection.execute(text('CREATE INDEX IF NOT EXISTS ix_games_updated_at ON games (updated_at)'))
=======
    if alter_statements:
        with engine.begin() as connection:
            for statement in alter_statements:
                connection.execute(text(statement))
            connection.execute(text("UPDATE games SET categoria = 'Biblioteca' WHERE categoria IS NULL OR categoria = ''"))
            connection.execute(text("UPDATE games SET prioridad = 'Media' WHERE prioridad IS NULL OR prioridad = ''"))
            connection.execute(text(f'UPDATE games SET es_favorito = {default_false} WHERE es_favorito IS NULL'))

    # Asegurar índices para filtros y ordenamientos comunes (Fuera del bloque condicional para mayor robustez)
    with engine.begin() as connection:
        connection.execute(text('CREATE INDEX IF NOT EXISTS ix_games_created_at ON games (created_at)'))
        connection.execute(text('CREATE INDEX IF NOT EXISTS ix_games_updated_at ON games (updated_at)'))
>>>>>>> REPLACE
