import { Box, Heading, Stack } from "@fidesui/react";
import { ReactNode } from "react";

const FormSection = ({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) => (
  <Box borderRadius="md" border="1px solid" borderColor="gray.200">
    <Heading
      as="h3"
      fontSize="sm"
      fontWeight="semibold"
      color="gray.700"
      py={4}
      px={6}
      backgroundColor="gray.50"
      borderRadius="md"
      textAlign="left"
    >
      {title}
    </Heading>
    <Stack p={6} spacing={6}>
      {children}
    </Stack>
  </Box>
);

export default FormSection;
