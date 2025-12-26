"""
Tests for CongressMembersIngester.

Tests the ingester's ability to fetch, transform, and load Congress member data.
Uses mocking to avoid requiring API keys or database connections.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
import httpx

from src.ingestion.congress_members import CongressMembersIngester
from src.models.politician import Politician, Chamber, Party


@pytest.fixture
def sample_member_data():
    """Sample member data as returned by Congress.gov API."""
    return {
        "bioguideId": "L000577",
        "name": "Lee, Mike",
        "partyName": "Republican",
        "state": "UT",
        "district": None,
        "officialWebsiteUrl": "https://www.lee.senate.gov",
        "terms": {
            "item": [
                {
                    "chamber": "Senate",
                    "startYear": 2011,
                    "endYear": 2017
                },
                {
                    "chamber": "Senate",
                    "startYear": 2017,
                    "endYear": 2023
                },
                {
                    "chamber": "Senate",
                    "startYear": 2023,
                    "endYear": 2029
                }
            ]
        },
        "state_code": "UT"
    }


@pytest.fixture
def sample_house_member_data():
    """Sample House member data."""
    return {
        "bioguideId": "O000086",
        "name": "Owens, Burgess",
        "partyName": "Republican",
        "state": "UT",
        "district": 4,
        "officialWebsiteUrl": "https://owens.house.gov",
        "terms": {
            "item": [
                {
                    "chamber": "House of Representatives",
                    "startYear": 2021,
                    "endYear": 2023
                },
                {
                    "chamber": "House of Representatives",
                    "startYear": 2023,
                    "endYear": 2025
                }
            ]
        },
        "state_code": "UT"
    }


@pytest.fixture
def sample_member_details():
    """Sample detailed member data from the /member/{bioguideId} endpoint."""
    return {
        "member": {
            "bioguideId": "L000577",
            "addressInformation": {
                "officeAddress": [
                    {
                        "line1": "361A Russell Senate Office Building",
                        "line2": "",
                        "city": "Washington",
                        "state": "DC",
                        "zip": "20510",
                        "phoneNumber": "202-224-5444"
                    }
                ]
            }
        }
    }


@pytest.fixture
def ingester():
    """Create a CongressMembersIngester instance with mocked database."""
    with patch('src.ingestion.congress_members.settings') as mock_settings:
        mock_settings.CONGRESS_GOV_API_KEY = "test_api_key"
        ingester = CongressMembersIngester(congress=118, fetch_details=False)

        # Mock the database
        ingester.db = MagicMock()
        ingester.db.politicians = AsyncMock()

        return ingester


class TestCongressMembersIngester:
    """Test suite for CongressMembersIngester."""

    def test_init_basic(self):
        """Test basic initialization."""
        with patch('src.ingestion.congress_members.settings') as mock_settings:
            mock_settings.CONGRESS_GOV_API_KEY = "test_key"
            ingester = CongressMembersIngester()

            assert ingester.congress == 118
            assert ingester.state_filter is None
            assert ingester.chamber_filter is None
            assert ingester.fetch_details is True

    def test_init_with_filters(self):
        """Test initialization with state and chamber filters."""
        with patch('src.ingestion.congress_members.settings') as mock_settings:
            mock_settings.CONGRESS_GOV_API_KEY = "test_key"
            ingester = CongressMembersIngester(
                congress=119,
                state_filter="ut",
                chamber_filter="SENATE",
                fetch_details=False
            )

            assert ingester.congress == 119
            assert ingester.state_filter == "UT"  # Should be uppercase
            assert ingester.chamber_filter == "senate"  # Should be lowercase
            assert ingester.fetch_details is False

    def test_extract_chamber_senate(self, ingester, sample_member_data):
        """Test _extract_chamber returns 'senate' for Senate members."""
        chamber = ingester._extract_chamber(sample_member_data)
        assert chamber == "senate"

    def test_extract_chamber_house(self, ingester, sample_house_member_data):
        """Test _extract_chamber returns 'house' for House members."""
        chamber = ingester._extract_chamber(sample_house_member_data)
        assert chamber == "house"

    def test_extract_chamber_no_terms(self, ingester):
        """Test _extract_chamber returns None when no terms available."""
        member_data = {"terms": {"item": []}}
        chamber = ingester._extract_chamber(member_data)
        assert chamber is None

    @pytest.mark.asyncio
    async def test_transform_senate_member(self, ingester, sample_member_data):
        """Test transforming a Senate member to Politician model."""
        politician = await ingester.transform(sample_member_data)

        assert isinstance(politician, Politician)
        assert politician.bioguide_id == "L000577"
        assert politician.first_name == "Mike"
        assert politician.last_name == "Lee"
        assert politician.full_name == "Mike Lee"
        assert politician.party == Party.REPUBLICAN
        assert politician.state == "UT"
        assert politician.chamber == Chamber.SENATE
        assert politician.district is None
        assert politician.title == "Senator"
        assert politician.in_office is True
        assert politician.website == "https://www.lee.senate.gov"

    @pytest.mark.asyncio
    async def test_transform_house_member(self, ingester, sample_house_member_data):
        """Test transforming a House member to Politician model."""
        politician = await ingester.transform(sample_house_member_data)

        assert isinstance(politician, Politician)
        assert politician.bioguide_id == "O000086"
        assert politician.first_name == "Burgess"
        assert politician.last_name == "Owens"
        assert politician.full_name == "Burgess Owens"
        assert politician.party == Party.REPUBLICAN
        assert politician.chamber == Chamber.HOUSE
        assert politician.district == 4
        assert politician.title == "Representative"

    @pytest.mark.asyncio
    async def test_transform_with_details(self, ingester, sample_member_data, sample_member_details):
        """Test transforming member data with detailed contact information."""
        # Add details to member data
        sample_member_data["_details"] = sample_member_details["member"]

        politician = await ingester.transform(sample_member_data)

        assert politician.office == "361A Russell Senate Office Building, Washington, DC 20510"
        assert politician.phone == "202-224-5444"

    @pytest.mark.asyncio
    async def test_transform_democrat(self, ingester, sample_member_data):
        """Test party mapping for Democrats."""
        sample_member_data["partyName"] = "Democratic"
        politician = await ingester.transform(sample_member_data)
        assert politician.party == Party.DEMOCRAT

    @pytest.mark.asyncio
    async def test_transform_independent(self, ingester, sample_member_data):
        """Test party mapping for Independents."""
        sample_member_data["partyName"] = "Independent"
        politician = await ingester.transform(sample_member_data)
        assert politician.party == Party.INDEPENDENT

    @pytest.mark.asyncio
    async def test_transform_missing_bioguide_id(self, ingester, sample_member_data):
        """Test that transform raises ValueError when bioguideId is missing."""
        del sample_member_data["bioguideId"]

        with pytest.raises(ValueError, match="Missing bioguideId"):
            await ingester.transform(sample_member_data)

    @pytest.mark.asyncio
    async def test_fetch_member_details_success(self, ingester, sample_member_details):
        """Test fetching member details successfully."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = sample_member_details
        mock_client.get.return_value = mock_response

        details = await ingester.fetch_member_details("L000577", mock_client)

        assert details == sample_member_details["member"]
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_member_details_http_error(self, ingester):
        """Test fetch_member_details handles HTTP errors gracefully."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("API Error")

        details = await ingester.fetch_member_details("L000577", mock_client)

        assert details is None

    @pytest.mark.asyncio
    async def test_load_new_senator(self, ingester, sample_member_data):
        """Test loading a new Senator into database."""
        politician = await ingester.transform(sample_member_data)

        # Mock the update_one to return upserted_id (new insert)
        mock_result = MagicMock()
        mock_result.upserted_id = "some_id"
        mock_result.modified_count = 0
        ingester.db.politicians.update_one = AsyncMock(return_value=mock_result)

        was_insert = await ingester.load(politician)

        assert was_insert is True
        ingester.db.politicians.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_existing_senator(self, ingester, sample_member_data):
        """Test updating an existing Senator in database."""
        politician = await ingester.transform(sample_member_data)

        # Mock the update_one to return no upserted_id (update)
        mock_result = MagicMock()
        mock_result.upserted_id = None
        mock_result.modified_count = 1
        ingester.db.politicians.update_one = AsyncMock(return_value=mock_result)

        was_insert = await ingester.load(politician)

        assert was_insert is False

    @pytest.mark.asyncio
    async def test_load_house_member_marks_old_out_of_office(self, ingester, sample_house_member_data):
        """Test that loading a House member marks previous occupant as out of office."""
        politician = await ingester.transform(sample_house_member_data)

        # Mock update_many to simulate marking old member out of office
        mock_update_many_result = MagicMock()
        mock_update_many_result.modified_count = 1
        ingester.db.politicians.update_many = AsyncMock(return_value=mock_update_many_result)

        # Mock update_one for the new member
        mock_update_one_result = MagicMock()
        mock_update_one_result.upserted_id = "new_id"
        ingester.db.politicians.update_one = AsyncMock(return_value=mock_update_one_result)

        await ingester.load(politician)

        # Verify update_many was called to mark old member out of office
        ingester.db.politicians.update_many.assert_called_once()
        call_args = ingester.db.politicians.update_many.call_args
        query = call_args[0][0]

        assert query["state"] == "UT"
        assert query["district"] == 4
        assert query["chamber"] == "house"
        assert query["in_office"] is True
        assert query["bioguide_id"]["$ne"] == "O000086"

    @pytest.mark.asyncio
    async def test_fetch_data_with_state_filter(self, ingester):
        """Test fetch_data respects state filter."""
        ingester.state_filter = "UT"

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "members": [
                {"bioguideId": "L000577", "name": "Lee, Mike", "terms": {"item": [{"chamber": "Senate"}]}}
            ]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            members = []
            async for member in ingester.fetch_data():
                members.append(member)

            # Should only call API once for UT
            assert mock_client.get.call_count == 1
            assert len(members) == 1
            assert members[0]["bioguideId"] == "L000577"

    @pytest.mark.asyncio
    async def test_fetch_data_with_chamber_filter(self, ingester):
        """Test fetch_data filters by chamber."""
        ingester.state_filter = "UT"
        ingester.chamber_filter = "senate"

        # Mock HTTP response with both Senate and House members
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "members": [
                {
                    "bioguideId": "L000577",
                    "name": "Lee, Mike",
                    "terms": {"item": [{"chamber": "Senate"}]}
                },
                {
                    "bioguideId": "O000086",
                    "name": "Owens, Burgess",
                    "terms": {"item": [{"chamber": "House of Representatives"}]}
                }
            ]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            members = []
            async for member in ingester.fetch_data():
                members.append(member)

            # Should only yield Senate member
            assert len(members) == 1
            assert members[0]["bioguideId"] == "L000577"

    @pytest.mark.asyncio
    async def test_fetch_data_handles_404(self, ingester):
        """Test fetch_data handles 404 responses gracefully."""
        ingester.state_filter = "XX"  # Non-existent state

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            members = []
            async for member in ingester.fetch_data():
                members.append(member)

            assert len(members) == 0

    @pytest.mark.asyncio
    async def test_fetch_data_with_details(self, ingester, sample_member_details):
        """Test fetch_data fetches detailed member information when enabled."""
        ingester.fetch_details = True
        ingester.state_filter = "UT"

        # Mock main member response
        mock_member_response = MagicMock()
        mock_member_response.status_code = 200
        mock_member_response.json.return_value = {
            "members": [
                {"bioguideId": "L000577", "name": "Lee, Mike", "terms": {"item": [{"chamber": "Senate"}]}}
            ]
        }

        # Mock details response
        mock_details_response = MagicMock()
        mock_details_response.json.return_value = sample_member_details

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()

            # First call returns member list, second call returns details
            mock_client.get = AsyncMock(side_effect=[mock_member_response, mock_details_response])
            mock_client_class.return_value = mock_client

            members = []
            async for member in ingester.fetch_data():
                members.append(member)

            assert len(members) == 1
            assert "_details" in members[0]
            assert members[0]["_details"] == sample_member_details["member"]
            # Should call API twice: once for members, once for details
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_run_full_sync(self, ingester):
        """Test run_full_sync executes the full pipeline."""
        with patch.object(ingester, 'run') as mock_run:
            mock_run.return_value = {
                "processed": 5,
                "inserted": 3,
                "updated": 2,
                "errors": 0
            }

            stats = await ingester.run_full_sync()

            assert stats["processed"] == 5
            assert stats["inserted"] == 3
            assert stats["updated"] == 2
            mock_run.assert_called_once()
