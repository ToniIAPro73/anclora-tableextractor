# TableExtractor VPS production

TableExtractor runs as the `anclora/tableextractor-api:<main-sha>` image on the
Contabo VPS. Caddy exposes it only as
`https://api.tableextractor.anclora.com` and proxies to loopback port 8101.

The container runs as a non-root user. Production configuration is kept outside
the repository at `/home/toni/.config/anclora/runtime/tableextractor.env`.
Database schema changes are owned by Alembic; runtime startup only checks Neon
connectivity. Production images are built from the promoted `main` SHA.
