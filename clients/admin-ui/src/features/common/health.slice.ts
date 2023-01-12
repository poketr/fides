import { createSelector } from "@reduxjs/toolkit";
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

import type { RootState } from "~/app/store";
import { CoreHealthCheck } from "~/types/api";

export const healthApi = createApi({
  reducerPath: "healthApi",
  baseQuery: fetchBaseQuery({
    baseUrl: `/`,
  }),
  tagTypes: ["Health"],
  endpoints: (build) => ({
    getHealth: build.query<CoreHealthCheck, void>({
      query: () => "health",
    }),
  }),
});

export const { useGetHealthQuery } = healthApi;

export const selectHealth: (state: RootState) => CoreHealthCheck | undefined =
  createSelector(healthApi.endpoints.getHealth.select(), ({ data }) => data);
