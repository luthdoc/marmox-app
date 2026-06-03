-- Seed de desenvolvimento: tenant + leads de teste
-- Executar apenas uma vez após as migrations 001–006

INSERT INTO tenants (id, name, status, user_id, services, regions, business_hours, welcome_message)
VALUES (
  'a1b2c3d4-0000-0000-0000-000000000001',
  'Marmoraria Demo',
  'active',
  'c4cc0c3b-65ac-4eb9-b966-3839b4e44526',
  ARRAY['Bancadas', 'Pias', 'Soleiras', 'Escadas', 'Revestimentos'],
  ARRAY['São Paulo', 'ABC Paulista', 'Guarulhos'],
  'Segunda a Sexta, 8h às 18h. Sábado, 8h às 13h.',
  'Olá! Sou o assistente da Marmoraria Demo. Como posso ajudar com seu projeto?'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO leads (id, tenant_id, phone, name, status, service_type, material, urgency, neighborhood, last_contact_at)
VALUES
  (
    'b1000000-0000-0000-0000-000000000001',
    'a1b2c3d4-0000-0000-0000-000000000001',
    '5511991110001', 'Ana Lima', 'qualified',
    'Bancada de cozinha', 'Mármore Carrara', 'alta', 'Moema',
    now() - interval '2 hours'
  ),
  (
    'b1000000-0000-0000-0000-000000000002',
    'a1b2c3d4-0000-0000-0000-000000000001',
    '5511991110002', 'Carlos Souza', 'new',
    'Pia de banheiro', 'Granito Preto São Gabriel', 'media', 'Pinheiros',
    now() - interval '1 day'
  ),
  (
    'b1000000-0000-0000-0000-000000000003',
    'a1b2c3d4-0000-0000-0000-000000000001',
    '5511991110003', 'Fernanda Costa', 'scheduled',
    'Soleira e peitoril', 'Pedra Miracema', 'baixa', 'Vila Madalena',
    now() - interval '3 hours'
  ),
  (
    'b1000000-0000-0000-0000-000000000004',
    'a1b2c3d4-0000-0000-0000-000000000001',
    '5511991110004', 'Roberto Nunes', 'qualifying',
    'Escada completa', 'Granito Amarelo Ornamental', 'alta', 'Santo André',
    now() - interval '30 minutes'
  ),
  (
    'b1000000-0000-0000-0000-000000000005',
    'a1b2c3d4-0000-0000-0000-000000000001',
    '5511991110005', 'Juliana Martins', 'cold',
    'Bancada de lavabo', 'Quartzo Branco', 'baixa', 'Higienópolis',
    now() - interval '10 days'
  )
ON CONFLICT (id) DO NOTHING;
