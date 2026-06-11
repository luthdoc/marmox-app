-- Vincula o número WhatsApp do tenant ao phone_number_id da Meta Cloud API.
-- Aplica apenas em tenants que ainda não têm whatsapp_phone_number_id definido.

UPDATE tenants
SET whatsapp_phone_number_id = '1220170564507810'
WHERE whatsapp_phone_number_id IS NULL;
