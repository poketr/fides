import { Box, Breadcrumb, BreadcrumbItem, Heading, Text } from "@fidesui/react";
import type { NextPage } from "next";
import NextLink from "next/link";

import { useSystemOrDatamapRoute } from "~/features/common/hooks/useSystemOrDatamapRoute";
import Layout from "~/features/common/Layout";
import {
  ADD_SYSTEMS_ROUTE,
  DATAMAP_ROUTE,
} from "~/features/common/nav/v2/routes";
import { AddMultipleSystems } from "~/features/system/AddMultipleSystems";

const DESCRIBE_SYSTEM_COPY =
  "Select and add systems directory to your data map. ALl s ystems available here are from the TCF Global Vendor list, Google's AC list, and Fides Compass. All Systems come pre-configured so there is no need for your to do anything!";

const Header = () => (
  <Box display="flex" mb={2} alignItems="center" data-testid="header">
    <Heading fontSize="2xl" fontWeight="semibold">
      Add systems
    </Heading>
  </Box>
);

const AddMultipleSystemsPage: NextPage = () => {
  const { systemOrDatamapRoute } = useSystemOrDatamapRoute();

  return (
    <Layout title="Describe your system">
      <Box mb={4}>
        <Header />
        <Box>
          <Breadcrumb
            fontWeight="medium"
            fontSize="sm"
            color="gray.600"
            data-testid="breadcrumbs"
          >
            <BreadcrumbItem>
              <NextLink href={systemOrDatamapRoute}>Data map</NextLink>
            </BreadcrumbItem>
            <BreadcrumbItem>
              <NextLink href={ADD_SYSTEMS_ROUTE}>Add systems</NextLink>
            </BreadcrumbItem>
          </Breadcrumb>
        </Box>
      </Box>
      <Box w={{ base: "100%", md: "75%" }}>
        <Text fontSize="sm" mb={8}>
          {DESCRIBE_SYSTEM_COPY}
        </Text>
      </Box>
      <AddMultipleSystems redirectRoute={DATAMAP_ROUTE} />
    </Layout>
  );
};

export default AddMultipleSystemsPage;
