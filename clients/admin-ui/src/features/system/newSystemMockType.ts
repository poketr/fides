export type NewDeclaration = {
  name: string;
  data_categories?: string[];
  data_use: string;
  data_subjects?: string[];
  egress?: string;
  ingress?: string;
  features?: string[];
  legal_basis_for_processing?: string;
  impact_assessment_location?: string;
  retention_period?: number;
  processes_special_category_data: boolean;
  special_category_legal_basis?: string;
  data_shared_with_third_parties: boolean;
  third_parties?: string;
  shared_categories: string[];
  cookies: string[];
  id: string;
};

export type NewSystem = {
  fides_key: string;
  organization_fides_key: string;
  tags: string[];
  name: string;
  description: string;
  registry_id?: string;
  meta?: string;
  fidesctl_meta?: string;
  system_type: string;
  destination?: {
    fides_key: string;
    type: string;
    data_categories?: string[];
  }[];
  source?: {
    fides_key: string;
    type: string;
    data_categories?: string[];
  }[];
  privacy_declarations: NewDeclaration[];
  administrating_department: string;
  vendor_id: string;
  processes_personal_data: boolean;
  exempt_from_privacy_regulations: boolean;
  reason_for_exemption?: string;
  uses_profiling: boolean;
  legal_basis_for_profiling: string;
  does_international_transfers: boolean;
  legal_basis_for_transfers: string;
  requires_data_protection_assessments: boolean;
  dpa_location: string;
  dpa_progress: string;
  privacy_policy: string;
  legal_name: string;
  legal_address: string;
  responsibility: string[];
  dpo: string;
  joint_controller_info: string;
  data_security_practices?: string[];
  connection_configs?: string[];
  cookies: string[];
};
