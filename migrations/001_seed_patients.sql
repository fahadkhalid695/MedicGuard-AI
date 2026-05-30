-- MediGuard AI - Seed Data (10 demo patients)
-- =============================================

INSERT INTO patients (id, first_name, last_name, date_of_birth, gender, conditions, medications, emergency_contact)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'Sarah', 'Johnson', '1965-03-15', 'Female',
   ARRAY['Hypertension', 'Hyperlipidemia'],
   '[{"name": "Lisinopril", "dosage": "10mg", "frequency": "daily"}]'::jsonb,
   '{"name": "Tom Johnson", "phone": "+15551001001", "relationship": "Spouse", "patient_phone": "+15552001001"}'::jsonb),

  ('00000000-0000-0000-0000-000000000002', 'Michael', 'Chen', '1978-07-22', 'Male',
   ARRAY['Type 2 Diabetes'],
   '[{"name": "Metformin", "dosage": "500mg", "frequency": "twice daily"}]'::jsonb,
   '{"name": "Linda Chen", "phone": "+15551002002", "relationship": "Spouse", "patient_phone": "+15552002002"}'::jsonb),

  ('00000000-0000-0000-0000-000000000003', 'Emily', 'Rodriguez', '1990-11-08', 'Female',
   ARRAY['Asthma'],
   '[{"name": "Albuterol", "dosage": "90mcg", "frequency": "as needed"}]'::jsonb,
   '{"name": "Carlos Rodriguez", "phone": "+15551003003", "relationship": "Father", "patient_phone": "+15552003003"}'::jsonb),

  ('00000000-0000-0000-0000-000000000004', 'James', 'Williams', '1955-01-30', 'Male',
   ARRAY['COPD', 'Heart Failure'],
   '[{"name": "Furosemide", "dosage": "40mg", "frequency": "daily"}, {"name": "Tiotropium", "dosage": "18mcg", "frequency": "daily"}]'::jsonb,
   '{"name": "Mary Williams", "phone": "+15551004004", "relationship": "Spouse", "patient_phone": "+15552004004"}'::jsonb),

  ('00000000-0000-0000-0000-000000000005', 'Maria', 'Garcia', '1982-09-12', 'Female',
   ARRAY['Arrhythmia'],
   '[{"name": "Metoprolol", "dosage": "25mg", "frequency": "twice daily"}]'::jsonb,
   '{"name": "Jose Garcia", "phone": "+15551005005", "relationship": "Spouse", "patient_phone": "+15552005005"}'::jsonb),

  ('00000000-0000-0000-0000-000000000006', 'Robert', 'Brown', '1970-04-25', 'Male',
   ARRAY['Hypertension'],
   '[{"name": "Amlodipine", "dosage": "5mg", "frequency": "daily"}]'::jsonb,
   '{"name": "Susan Brown", "phone": "+15551006006", "relationship": "Spouse", "patient_phone": "+15552006006"}'::jsonb),

  ('00000000-0000-0000-0000-000000000007', 'Lisa', 'Davis', '1988-12-03', 'Female',
   ARRAY['Anxiety', 'Insomnia'],
   '[{"name": "Sertraline", "dosage": "50mg", "frequency": "daily"}]'::jsonb,
   '{"name": "Mark Davis", "phone": "+15551007007", "relationship": "Spouse", "patient_phone": "+15552007007"}'::jsonb),

  ('00000000-0000-0000-0000-000000000008', 'David', 'Wilson', '1960-06-18', 'Male',
   ARRAY['Coronary Artery Disease'],
   '[{"name": "Aspirin", "dosage": "81mg", "frequency": "daily"}, {"name": "Atorvastatin", "dosage": "40mg", "frequency": "daily"}]'::jsonb,
   '{"name": "Karen Wilson", "phone": "+15551008008", "relationship": "Spouse", "patient_phone": "+15552008008"}'::jsonb),

  ('00000000-0000-0000-0000-000000000009', 'Jennifer', 'Taylor', '1975-08-27', 'Female',
   ARRAY['Hypothyroidism'],
   '[{"name": "Levothyroxine", "dosage": "75mcg", "frequency": "daily"}]'::jsonb,
   '{"name": "Brian Taylor", "phone": "+15551009009", "relationship": "Spouse", "patient_phone": "+15552009009"}'::jsonb),

  ('00000000-0000-0000-0000-000000000010', 'Thomas', 'Anderson', '1952-02-14', 'Male',
   ARRAY['Atrial Fibrillation', 'Hypertension'],
   '[{"name": "Warfarin", "dosage": "5mg", "frequency": "daily"}, {"name": "Diltiazem", "dosage": "120mg", "frequency": "daily"}]'::jsonb,
   '{"name": "Patricia Anderson", "phone": "+15551010010", "relationship": "Spouse", "patient_phone": "+15552010010"}'::jsonb)
ON CONFLICT (id) DO NOTHING;
