-- Executar uma vez no banco configurado em URL_DATABASE.
-- O IF NOT EXISTS permite repetir com segurança no MySQL 8+.
ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS title VARCHAR(120) NOT NULL DEFAULT 'Compra'
    AFTER id;
