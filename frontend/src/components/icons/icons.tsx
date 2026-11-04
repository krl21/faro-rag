import { Icon, type IconProps } from './Icon';

export const LighthouseIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M10 3h4l1 4H9l1-4Z" />
    <path d="M9 7 7 21h10L15 7" />
    <path d="M8.3 12h7.4M7.7 16.5h8.6" />
    <path d="M17 4.5 20 3M17 6.5h3.5M7 4.5 4 3M7 6.5H3.5" />
  </Icon>
);

export const DocumentIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" />
    <path d="M14 3v5h5M9 13h6M9 17h6" />
  </Icon>
);

export const ChatIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z" />
  </Icon>
);

export const FieldsIcon = (props: IconProps) => (
  <Icon {...props}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M7 9h4M7 13h4M7 17h4M14 9h3M14 13h3M14 17h3" />
  </Icon>
);

export const UploadIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 16V4M7 9l5-5 5 5" />
    <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
  </Icon>
);

export const WarningIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M10.3 3.9 2.4 17.6A2 2 0 0 0 4.1 20.6h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
    <path d="M12 9v4M12 17h.01" />
  </Icon>
);

export const InfoIcon = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5M12 8h.01" />
  </Icon>
);

export const CloseIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Icon>
);

export const EditIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 20h4L19 9l-4-4L4 16v4Z" />
    <path d="M13.5 6.5l4 4" />
  </Icon>
);

export const SendIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 12 20 4l-6 16-3-7-7-1Z" />
  </Icon>
);

export const PlusIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 5v14M5 12h14" />
  </Icon>
);
